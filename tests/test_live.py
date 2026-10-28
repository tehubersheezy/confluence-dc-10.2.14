"""Integration tests against the local Confluence DC instance, as the non-admin user.

set -a; source .env; set +a
uv run pytest -m live
"""

import os
import uuid

import pytest

from confluence_dc import AsyncConfluence, Confluence, NotFoundError, PermissionDeniedError

URL = os.environ.get("CONFLUENCE_URL", "http://localhost:8095")
TOKEN = os.environ.get("CONFLUENCE_USER_PAT")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not TOKEN, reason="set CONFLUENCE_USER_PAT to run live tests"),
]


@pytest.fixture(scope="module")
def c():
    with Confluence(URL, token=TOKEN) as client:
        yield client


@pytest.fixture(scope="module")
def space(c):
    """The test user's personal space, where a regular user has admin rights."""
    me = c.users.current()["username"]
    try:
        return c.spaces.get(f"~{me}")["key"]
    except NotFoundError:
        return c.spaces.create_personal({"name": me})["key"]


@pytest.fixture
def page(c, space):
    created = c.content.create(
        {
            "type": "page",
            "title": f"lib-test {uuid.uuid4().hex[:8]}",
            "space": {"key": space},
            "body": {"storage": {"value": "<p>v1</p>", "representation": "storage"}},
        }
    )
    yield created
    try:
        c.content.delete(created["id"])
    except NotFoundError:
        pass


def test_current_user(c):
    me = c.users.current()
    assert me["type"] == "known" and me["username"]


def test_page_update_labels_properties(c, page):
    pid = page["id"]
    updated = c.content.update(
        pid,
        {
            "type": "page",
            "title": page["title"],
            "version": {"number": 2},
            "body": {"storage": {"value": "<p>v2</p>", "representation": "storage"}},
        },
    )
    assert updated["version"]["number"] == 2
    got = c.content.get(pid, expand="body.storage")
    assert got["body"]["storage"]["value"] == "<p>v2</p>"

    c.labels.add_to_content(pid, [{"prefix": "global", "name": "lib-test"}])
    assert [x["name"] for x in c.labels.for_content(pid)["results"]] == ["lib-test"]
    c.labels.remove_from_content(pid, "lib-test")
    assert c.labels.for_content(pid)["results"] == []

    c.content_properties.create(pid, {"key": "lib.test", "value": {"n": 1}})
    assert c.content_properties.get(pid, "lib.test")["value"] == {"n": 1}
    c.content_properties.delete(pid, "lib.test")
    with pytest.raises(NotFoundError):
        c.content_properties.get(pid, "lib.test")


def test_attachment_round_trip(c, page):
    data = b"hello from confluence-dc " + uuid.uuid4().bytes
    res = c.attachments.create(
        page["id"], {"file": ("hello.txt", data, "text/plain")}, data={"comment": "lib-test"}
    )
    att = res["results"][0]
    assert att["title"] == "hello.txt"
    listed = c.attachments.list(page["id"], filename="hello.txt")["results"]
    assert listed[0]["id"] == att["id"]
    assert c.download(listed[0]["_links"]["download"]) == data
    c.attachments.delete(page["id"], att["id"])


def test_cql_search_paginates(c):
    # Uses existing content: the search index picks up new pages asynchronously.
    cql = "space = TEST and type = page"
    total = c.search.cql(cql=cql, limit=1)["totalSize"]
    hits = list(c.paginate(c.search.cql, cql=cql, limit=40))
    assert total > 40
    assert len(hits) == len({h["content"]["id"] for h in hits}) == total


def test_template_lifecycle(c, space):
    tmpl = c.experimental.templates.create(
        {
            "name": f"lib-test {uuid.uuid4().hex[:8]}",
            "templateType": "page",
            "description": "test",
            "body": {
                "storage": {
                    "value": "<p>From <strong>template</strong></p>",
                    "representation": "storage",
                }
            },
            "labels": [{"prefix": "global", "name": "lib-test"}],
            "space": {"key": space},
        }
    )
    tid = tmpl["templateId"]
    try:
        assert c.experimental.templates.get(tid)["body"]["storage"]["value"].startswith("<p>From")
        listed = {
            t["templateId"] for t in c.paginate(c.experimental.templates.list, space_key=space)
        }
        assert tid in listed

        renamed = c.experimental.templates.update(
            {
                "templateId": tid,
                "name": tmpl["name"] + " v2",
                "templateType": "page",
                "description": "test",
                "body": tmpl.get("body") or c.experimental.templates.get(tid)["body"],
                "space": {"key": space},
            }
        )
        assert renamed["name"].endswith(" v2")

        inst = c.experimental.templates.create_content(
            tid,
            {
                "content": {
                    "type": "page",
                    "title": f"from template {tid}",
                    "space": {"key": space},
                },
                "contentBlueprintSpec": {"contentTemplateId": tid, "context": {}},
            },
        )
        new_id = inst["content"]["id"]
        body = c.content.get(new_id, expand="body.storage")["body"]["storage"]["value"]
        assert body == "<p>From <strong>template</strong></p>"
        c.content.delete(new_id)
    finally:
        c.experimental.templates.delete(tid)
    # Confluence answers 403 ("Cannot get template") for a deleted template.
    with pytest.raises((NotFoundError, PermissionDeniedError)):
        c.experimental.templates.get(tid)


def test_internal_likes(c, page):
    c.internal.likes.add_like(page["id"])
    likes = c.internal.likes.get_likes(page["id"])
    assert likes["likes"] and likes["likes"][0]["user"]["name"] == c.users.current()["username"]
    c.internal.likes.remove_like(page["id"])
    assert c.internal.likes.get_likes(page["id"])["likes"] == []


def test_not_found(c):
    with pytest.raises(NotFoundError):
        c.content.get("999999999")


async def test_async_client(space):
    async with AsyncConfluence(URL, token=TOKEN) as a:
        assert (await a.users.current())["username"]
        n = 0
        async for _ in a.paginate(a.content.list, space_key=space, limit=2):
            n += 1
        assert n >= 1
