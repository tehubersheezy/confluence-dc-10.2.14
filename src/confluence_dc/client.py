"""``Confluence`` (sync) and ``AsyncConfluence`` clients."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from typing import Any

import httpx

from ._api import ApiNamespaces
from ._endpoint import Call, decode, query_pairs
from .errors import TransportError, raise_for_status

DEFAULT_TIMEOUT = 30.0
_IDEMPOTENT = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


class _BaseClient(ApiNamespaces):
    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        auth: httpx.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        if token and (username or password):
            raise ValueError("pass either token or username/password, not both")
        if auth is None and token:
            auth = _Bearer(token)
        elif auth is None and username is not None:
            auth = httpx.BasicAuth(username, password or "")
        self._auth = auth
        self._headers = {
            "Accept": "application/json",
            # Confluence rejects most non-GET requests without this (XSRF check).
            "X-Atlassian-Token": "no-check",
            "User-Agent": "confluence-dc-python",
            **(headers or {}),
        }
        self.max_retries = max_retries
        ApiNamespaces.__init__(self)

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return self.base_url + (path if path.startswith("/") else "/" + path)

    def _retry_delay(
        self, attempt: int, method: str, response: httpx.Response | None
    ) -> float | None:
        """Seconds to wait before retrying, or None to give up."""
        if attempt >= self.max_retries:
            return None
        if response is not None:
            status = response.status_code
            if status == 429 or (status in (502, 503, 504) and method in _IDEMPOTENT):
                header = response.headers.get("Retry-After")
                try:
                    return min(float(header), 60.0) if header else _backoff(attempt)
                except ValueError:
                    return _backoff(attempt)
            return None
        return _backoff(attempt) if method in _IDEMPOTENT else None

    @staticmethod
    def _page_items(page: Any) -> list[Any]:
        if isinstance(page, dict):
            for key in ("results", "values", "items", "content"):
                if isinstance(page.get(key), list):
                    return page[key]
        if isinstance(page, list):
            return page
        raise TypeError("paginate() needs an endpoint that returns a page of results")

    @staticmethod
    def _next_page(
        page: Any, method: Callable[..., Any], kwargs: dict[str, Any]
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Return (next link, None) or (None, kwargs for the next start offset) or (None, None).

        Most endpoints return ``_links.next``. Some (CQL search) only report
        start/size/totalSize, so fall back to advancing ``start`` when the method takes it.
        """
        if not isinstance(page, dict):
            return None, None
        nxt = (page.get("_links") or {}).get("next")
        if nxt:
            return nxt, None
        size, limit, start = page.get("size"), page.get("limit"), page.get("start")
        if not all(isinstance(v, int) for v in (size, limit, start)) or not size:
            return None, None
        takes_start = "start" in kwargs or any(
            py == "start" for py, _ in getattr(getattr(method, "spec", None), "query", ())
        )
        total = page.get("totalSize")
        more = start + size < total if isinstance(total, int) else size >= limit
        if takes_start and more:
            return None, {**kwargs, "start": start + size}
        return None, None


def _backoff(attempt: int) -> float:
    return min(2**attempt, 30) * (0.5 + random.random() / 2)


class _Bearer(httpx.Auth):
    def __init__(self, token: str) -> None:
        self._value = f"Bearer {token}"

    def auth_flow(self, request: httpx.Request):  # type: ignore[override]
        request.headers["Authorization"] = self._value
        yield request


class Confluence(_BaseClient):
    """Blocking client.

    >>> with Confluence("http://localhost:8095", token="...") as c:
    ...     page = c.content.get("294916", expand="body.storage,version")
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        auth: httpx.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        verify: Any = True,
        max_retries: int = 3,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            base_url,
            token=token,
            username=username,
            password=password,
            auth=auth,
            headers=headers,
            max_retries=max_retries,
        )
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout, verify=verify)

    def __enter__(self) -> Confluence:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Mapping[str, Any] | None = None,
        files: Any = None,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
    ) -> Any:
        """Call any endpoint by path, e.g. ``request("GET", "/rest/api/space")``."""
        call = Call(
            method.upper(),
            path,
            raw=raw,
            json=json,
            files=files,
            data=dict(data) if data else None,
            headers=dict(headers or {}),
        )
        for k, v in (params or {}).items():
            call.params += query_pairs(k, v)
        return self._send(call)

    def _send(self, call: Call) -> Any:
        attempt = 0
        while True:
            try:
                response = self._http.request(
                    call.method,
                    self._url(call.path),
                    auth=self._auth,
                    **{**call.request_kwargs(), "headers": {**self._headers, **call.headers}},
                )
            except httpx.TransportError as exc:
                delay = self._retry_delay(attempt, call.method, None)
                if delay is None:
                    raise TransportError(str(exc)) from exc
            else:
                delay = (
                    None
                    if response.is_success
                    else self._retry_delay(attempt, call.method, response)
                )
                if delay is None:
                    if not call.raw:
                        raise_for_status(response)
                    return decode(response, call.raw)
            time.sleep(delay)
            attempt += 1

    def paginate(self, method: Callable[..., Any], *args: Any, **kwargs: Any) -> Iterator[Any]:
        """Yield every item across pages of a paged endpoint.

        >>> for page in c.paginate(c.content.list, space_key="TEST", type="page"):
        ...     print(page["title"])
        """
        page = method(*args, **kwargs)
        while True:
            yield from self._page_items(page)
            link, next_kwargs = self._next_page(page, method, kwargs)
            if link:
                page = self._send(Call("GET", link))
            elif next_kwargs:
                kwargs = next_kwargs
                page = method(*args, **kwargs)
            else:
                return

    def download(self, path_or_url: str) -> bytes:
        """Fetch a binary resource, e.g. an attachment's ``_links.download``."""
        response = self._send(Call("GET", path_or_url, headers={"Accept": "*/*"}, raw=True))
        raise_for_status(response)
        return response.content


class AsyncConfluence(_BaseClient):
    """Asyncio client. Every endpoint method returns an awaitable.

    >>> async with AsyncConfluence("http://localhost:8095", token="...") as c:
    ...     page = await c.content.get("294916")
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        auth: httpx.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        verify: Any = True,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            base_url,
            token=token,
            username=username,
            password=password,
            auth=auth,
            headers=headers,
            max_retries=max_retries,
        )
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout, verify=verify)

    async def __aenter__(self) -> AsyncConfluence:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Mapping[str, Any] | None = None,
        files: Any = None,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
    ) -> Any:
        """Call any endpoint by path, e.g. ``await request("GET", "/rest/api/space")``."""
        call = Call(
            method.upper(),
            path,
            raw=raw,
            json=json,
            files=files,
            data=dict(data) if data else None,
            headers=dict(headers or {}),
        )
        for k, v in (params or {}).items():
            call.params += query_pairs(k, v)
        return await self._send(call)

    async def _send(self, call: Call) -> Any:
        attempt = 0
        while True:
            try:
                response = await self._http.request(
                    call.method,
                    self._url(call.path),
                    auth=self._auth,
                    **{**call.request_kwargs(), "headers": {**self._headers, **call.headers}},
                )
            except httpx.TransportError as exc:
                delay = self._retry_delay(attempt, call.method, None)
                if delay is None:
                    raise TransportError(str(exc)) from exc
            else:
                delay = (
                    None
                    if response.is_success
                    else self._retry_delay(attempt, call.method, response)
                )
                if delay is None:
                    if not call.raw:
                        raise_for_status(response)
                    return decode(response, call.raw)
            await asyncio.sleep(delay)
            attempt += 1

    async def paginate(
        self, method: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> AsyncIterator[Any]:
        """Yield every item across pages of a paged endpoint.

        >>> async for page in c.paginate(c.content.list, space_key="TEST"):
        ...     print(page["title"])
        """
        page = await method(*args, **kwargs)
        while True:
            for item in self._page_items(page):
                yield item
            link, next_kwargs = self._next_page(page, method, kwargs)
            if link:
                page = await self._send(Call("GET", link))
            elif next_kwargs:
                kwargs = next_kwargs
                page = await method(*args, **kwargs)
            else:
                return

    async def download(self, path_or_url: str) -> bytes:
        """Fetch a binary resource, e.g. an attachment's ``_links.download``."""
        response = await self._send(Call("GET", path_or_url, headers={"Accept": "*/*"}, raw=True))
        raise_for_status(response)
        return response.content
