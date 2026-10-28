"""Exceptions raised by the client."""

from __future__ import annotations

from typing import Any

import httpx


class ConfluenceError(Exception):
    """Base class for every error this library raises."""


class TransportError(ConfluenceError):
    """The request never got an HTTP response (DNS, connect, timeout, TLS)."""


class APIError(ConfluenceError):
    """Confluence answered with a non-2xx status."""

    def __init__(self, response: httpx.Response, message: str, data: Any = None) -> None:
        self.response = response
        self.status_code = response.status_code
        self.method = response.request.method
        self.url = str(response.request.url)
        self.message = message
        self.data = data
        super().__init__(f"{self.status_code} {self.method} {self.url}: {message}")


class BadRequestError(APIError):
    """400: invalid parameters or body."""


class AuthenticationError(APIError):
    """401: missing, expired, or rejected credentials."""


class PermissionDeniedError(APIError):
    """403: authenticated, but not allowed (or XSRF check failed)."""


class NotFoundError(APIError):
    """404: the resource doesn't exist or isn't visible to this user."""


class ConflictError(APIError):
    """409: version conflict, duplicate title, and similar."""


class RateLimitError(APIError):
    """429: rate limited. ``retry_after`` is in seconds when the server sent it."""

    @property
    def retry_after(self) -> float | None:
        return _retry_after(self.response)


class ServerError(APIError):
    """5xx."""


_BY_STATUS: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _message_from(response: httpx.Response) -> tuple[str, Any]:
    """Pull a readable message out of the many error shapes Confluence plugins use."""
    text = response.text
    ctype = response.headers.get("content-type", "")
    if "json" in ctype:
        try:
            data = response.json()
        except ValueError:
            return text[:500] or response.reason_phrase, None
        if isinstance(data, dict):
            for key in ("message", "errorMessage", "error"):
                if isinstance(data.get(key), str) and data[key]:
                    return data[key], data
            msgs = data.get("errorMessages") or data.get("errors")
            if isinstance(msgs, list) and msgs:
                return "; ".join(
                    str(m.get("message", m) if isinstance(m, dict) else m) for m in msgs
                ), data
        return response.reason_phrase or str(data)[:500], data
    if "xml" in ctype and "<message>" in text:
        return text.split("<message>", 1)[1].split("</message>", 1)[0], None
    return (text.strip()[:500] or response.reason_phrase), None


def raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    message, data = _message_from(response)
    status = response.status_code
    cls = _BY_STATUS.get(status) or (ServerError if status >= 500 else APIError)
    raise cls(response, message, data)
