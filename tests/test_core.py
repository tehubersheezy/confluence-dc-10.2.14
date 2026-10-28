import json

import httpx
import pytest

from confluence_dc import (
    AsyncConfluence,
    AuthenticationError,
    Confluence,
    NotFoundError,
    RateLimitError,
    ServerError,
)


def make(handler, **kw):
    return Confluence(
        "https://wiki.example.com/confluence/",
        token="tok",
        max_retries=2,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        **kw,
    )


def make_async(handler, **kw):
    return AsyncConfluence(
        "https://wiki.example.com/confluence",
        token="tok",
        max_retries=2,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        **kw,
    )


def ok(payload=None, status=200):
    return httpx.Response(status, json=payload if payload is not None else {})


def test_auth_and_default_headers():
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return ok({"username": "me"})

    c = make(handler)
    assert c.users.current() == {"username": "me"}
    assert seen["authorization"] == "Bearer tok"
    assert seen["x-atlassian-token"] == "no-check"
    assert seen["accept"] == "application/json"


def test_basic_auth():
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return ok()

    Confluence(
        "https://x",
        username="u",
        password="p",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ).users.current()
    assert seen["authorization"].startswith("Basic ")


def test_token_and_password_conflict():
    with pytest.raises(ValueError):
        Confluence("https://x", token="t", username="u")


def test_path_query_and_context_path():
    seen = []
    c = make(lambda r: seen.append(r) or ok())
    c.labels.remove_from_content(123, "a/b c")
    c.content.list(space_key="DOCS", type="page", limit=5, expand=None)
    c.spaces.list(space_key=["A", "B"], favourite=True)
    assert seen[0].method == "DELETE"
    assert seen[0].url.raw_path == b"/confluence/rest/api/content/123/label/a%2Fb%20c"
    assert dict(seen[1].url.params) == {"spaceKey": "DOCS", "type": "page", "limit": "5"}
    assert seen[2].url.params.get_list("spaceKey") == ["A", "B"]
    assert seen[2].url.params["favourite"] == "true"


def test_json_body():
    seen = []
    c = make(lambda r: seen.append(r) or ok({"id": "1"}))
    c.content.create({"type": "page", "title": "T", "space": {"key": "DOCS"}}, expand="version")
    assert seen[0].method == "POST"
    assert seen[0].headers["content-type"] == "application/json"
    assert json.loads(seen[0].content)["title"] == "T"
    assert seen[0].url.params["expand"] == "version"


def test_multipart_upload():
    seen = []
    c = make(lambda r: seen.append(r) or ok({"results": []}))
    c.attachments.create(
        7,
        {"file": ("a.txt", b"hello", "text/plain")},
        data={"comment": "v1"},
        allow_duplicated=True,
    )
    req = seen[0]
    assert req.headers["content-type"].startswith("multipart/form-data")
    body = req.content.decode()
    assert 'filename="a.txt"' in body and "hello" in body and 'name="comment"' in body
    assert req.url.params["allowDuplicated"] == "true"


def test_vendor_accept_header():
    seen = []
    c = make(lambda r: seen.append(r) or ok())
    c.internal.plugins.get_plugin_collection()
    assert "application/vnd.atl.plugins" in seen[0].headers["accept"]


def test_error_mapping_json_and_xml():
    def handler(request):
        if "json" in request.url.path or request.url.path.endswith("/content/1"):
            return httpx.Response(404, json={"statusCode": 404, "message": "No content found"})
        return httpx.Response(
            401,
            text="<status><message>Not logged in</message></status>",
            headers={"content-type": "application/xml"},
        )

    c = make(handler)
    with pytest.raises(NotFoundError) as e:
        c.content.get(1)
    assert e.value.message == "No content found" and e.value.status_code == 404
    with pytest.raises(AuthenticationError) as e:
        c.users.current()
    assert e.value.message == "Not logged in"


def test_retries_429_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"message": "slow"})
        return ok({"ok": True})

    assert make(handler).content.create({"title": "x"}) == {"ok": True}
    assert len(calls) == 3


def test_retry_gives_up(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    c = make(lambda r: httpx.Response(429, json={"message": "slow"}))
    with pytest.raises(RateLimitError):
        c.users.current()


def test_no_retry_of_non_idempotent_5xx(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = []
    c = make(lambda r: calls.append(1) or httpx.Response(503, json={"message": "down"}))
    with pytest.raises(ServerError):
        c.content.create({"title": "x"})
    assert len(calls) == 1
    calls.clear()
    with pytest.raises(ServerError):
        c.content.get(1)
    assert len(calls) == 3


def _paged(request):
    start = int(request.url.params.get("start", 0))
    items = [{"id": str(i)} for i in range(start, min(start + 2, 5))]
    links = {}
    if start + 2 < 5:
        links["next"] = f"/rest/api/content?spaceKey=DOCS&limit=2&start={start + 2}"
    return ok({"results": items, "start": start, "limit": 2, "size": len(items), "_links": links})


def test_paginate_follows_next_link_and_keeps_its_query():
    seen = []
    c = make(lambda r: seen.append(r) or _paged(r))
    ids = [x["id"] for x in c.paginate(c.content.list, space_key="DOCS", limit=2)]
    assert ids == ["0", "1", "2", "3", "4"]
    assert seen[1].url.path == "/confluence/rest/api/content"
    assert seen[1].url.params["start"] == "2"


def test_paginate_by_offset_without_links():
    def handler(request):
        start = int(request.url.params.get("start", 0))
        items = [{"id": str(i)} for i in range(start, min(start + 2, 5))]
        return ok({"results": items, "start": start, "limit": 2, "size": len(items)})

    c = make(handler)
    assert len(list(c.paginate(c.content.list, limit=2, start=0))) == 5


def test_download_and_raw_bytes():
    c = make(
        lambda r: httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"})
    )
    assert c.download("/download/attachments/1/a.png") == b"\x89PNG"
    assert c.request("GET", "/x") == b"\x89PNG"


def test_request_escape_hatch():
    seen = []
    c = make(lambda r: seen.append(r) or httpx.Response(204))
    assert c.request("put", "/rest/api/admin/whatever", params={"a": 1}, json={"b": 2}) is None
    assert seen[0].method == "PUT" and seen[0].url.params["a"] == "1"


async def test_async_parity_and_pagination():
    seen = []
    async with make_async(lambda r: seen.append(r) or _paged(r)) as c:
        page = await c.content.list(space_key="DOCS", limit=2)
        assert page["size"] == 2
        ids = [x["id"] async for x in c.paginate(c.content.list, space_key="DOCS", limit=2)]
    assert ids == ["0", "1", "2", "3", "4"]
    assert seen[0].headers["authorization"] == "Bearer tok"


async def test_async_errors():
    c = make_async(lambda r: httpx.Response(404, json={"message": "nope"}))
    with pytest.raises(NotFoundError):
        await c.content.get(1)


def test_paginate_by_total_size_without_start_kwarg():
    # CQL search: no _links.next, reports totalSize; caller didn't pass start.
    seen = []

    def handler(request):
        seen.append(request)
        start = int(request.url.params.get("start", 0))
        items = [{"id": str(i)} for i in range(start, min(start + 2, 5))]
        return ok(
            {
                "results": items,
                "start": start,
                "limit": 2,
                "size": len(items),
                "totalSize": 5,
                "_links": {},
            }
        )

    c = make(handler)
    assert [x["id"] for x in c.paginate(c.search.cql, cql="type=page", limit=2)] == list("01234")
    assert len(seen) == 3
