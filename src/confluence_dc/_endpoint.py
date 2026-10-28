"""Endpoint declarations shared by the sync and async clients.

Each generated method is declared once with ``@endpoint``. Calling it binds the arguments
into a ``Call``, and the owning client (``Confluence`` or ``AsyncConfluence``) sends it, so
sync callers get the decoded value and async callers get an awaitable.
"""

from __future__ import annotations

import functools
import inspect
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

if TYPE_CHECKING:
    from .client import _BaseClient


@dataclass(frozen=True)
class Spec:
    method: str
    path: str
    # (python name, wire name) pairs
    path_params: tuple[tuple[str, str], ...] = ()
    query: tuple[tuple[str, str], ...] = ()
    form: tuple[tuple[str, str], ...] = ()
    headers: tuple[tuple[str, str], ...] = ()
    body: str | None = None
    multipart: bool = False
    consumes: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()


@dataclass
class Call:
    method: str
    path: str
    params: list[tuple[str, str]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    json: Any = None
    content: bytes | None = None
    data: dict[str, Any] | None = None
    files: Any = None
    raw: bool = False

    def request_kwargs(self) -> dict[str, Any]:
        kw: dict[str, Any] = {"headers": self.headers}
        # httpx replaces the URL's own query string when params is passed, even empty,
        # which would break followed `_links.next` URLs.
        if self.params:
            kw["params"] = self.params
        if self.json is not None:
            kw["json"] = self.json
        if self.content is not None:
            kw["content"] = self.content
        if self.data is not None:
            kw["data"] = self.data
        if self.files is not None:
            kw["files"] = self.files
        return kw


def wire_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def query_pairs(name: str, value: Any) -> list[tuple[str, str]]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set | frozenset):
        return [(name, wire_value(v)) for v in value if v is not None]
    return [(name, wire_value(value))]


def build_call(spec: Spec, args: Mapping[str, Any]) -> Call:
    path = spec.path
    for py, wire in spec.path_params:
        value = args[py]
        if value is None:
            raise ValueError(f"{py} is required")
        path = path.replace("{" + wire + "}", quote(wire_value(value), safe=""))

    call = Call(spec.method, path, raw=bool(args.get("raw")))
    for py, wire in spec.query:
        call.params += query_pairs(wire, args.get(py))
    extra = args.get("params")
    if extra:
        for k, v in dict(extra).items():
            call.params += query_pairs(k, v)

    for py, wire in spec.headers:
        if args.get(py) is not None:
            call.headers[wire] = wire_value(args[py])

    if spec.produces:
        call.headers["Accept"] = ", ".join(spec.produces)

    if spec.multipart:
        call.files = args.get("files")
        fields = {wire: wire_value(args[py]) for py, wire in spec.form if args.get(py) is not None}
        fields.update({k: wire_value(v) for k, v in (args.get("data") or {}).items()})
        call.data = fields or None
    elif spec.form:
        call.data = {
            wire: wire_value(args[py]) for py, wire in spec.form if args.get(py) is not None
        }
    elif spec.body is not None:
        body = args.get(spec.body)
        if body is not None:
            ctype = next((c for c in spec.consumes if "json" in c), None) or (
                spec.consumes[0] if spec.consumes else "application/json"
            )
            if isinstance(body, bytes):
                call.content = body
                call.headers["Content-Type"] = ctype
            elif isinstance(body, str) and "json" not in ctype:
                call.content = body.encode()
                call.headers["Content-Type"] = ctype
            else:
                call.content = json.dumps(body).encode()
                call.headers["Content-Type"] = ctype
    return call


def decode(response: httpx.Response, raw: bool = False) -> Any:
    if raw:
        return response
    if response.status_code == 204 or not response.content:
        return None
    ctype = response.headers.get("content-type", "").lower()
    if "json" in ctype:
        return response.json()
    if ctype.startswith("text/") or "xml" in ctype or "javascript" in ctype:
        return response.text
    return response.content


def endpoint(spec: Spec) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(self: Namespace, *args: Any, **kwargs: Any) -> Any:
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            return self._client._send(build_call(spec, bound.arguments))

        wrapper.spec = spec  # type: ignore[attr-defined]
        return wrapper

    return decorate


class Namespace:
    """A group of endpoints bound to one client."""

    def __init__(self, client: _BaseClient) -> None:
        self._client = client

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"
