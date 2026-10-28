#!/usr/bin/env python3
"""Publish the built templates to a Confluence DC space.

    set -a; source .env; set +a
    python3 templates/publish.py                   # pages under the space home
    python3 templates/publish.py --space-templates # also register as space page templates
    python3 templates/publish.py --check           # only report rendering errors

Environment: CONFLUENCE_URL (default http://localhost:8095), CONFLUENCE_PAT (required),
SPACE_KEY (default ITDOC), USER_KEY (default: the PAT's user), JIRA_APPLINK_ID
(default: the primary application link, or the Jira macros fall back to it).

Pages are upserted by title, so re-running updates them in place. Each page gets
the labels from manifest.json. The space home page body is replaced with 00-home.xml.
"""
import argparse, json, os, re, sys, html, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CONFLUENCE_URL", "http://localhost:8095").rstrip("/")
PAT = os.environ.get("CONFLUENCE_PAT") or sys.exit("CONFLUENCE_PAT is not set")
SPACE = os.environ.get("SPACE_KEY", "ITDOC")
H = {"Authorization": "Bearer " + PAT, "Content-Type": "application/json", "Accept": "application/json"}

def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method, headers=H)
    try:
        with urllib.request.urlopen(r) as x:
            raw = x.read()
            try:
                return x.status, (json.loads(raw) if raw else {})
            except json.JSONDecodeError:
                return x.status, raw.decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def fail(msg, resp):
    m = re.search(r'"message":"([^"]{0,200})', resp) if isinstance(resp, str) else None
    sys.exit(f"{msg}: {m.group(1) if m else str(resp)[:300]}")

def find_page(title):
    st, d = req("GET", f"/rest/api/content?spaceKey={SPACE}&title={urllib.parse.quote(title)}&expand=version")
    return d["results"][0] if st == 200 and d["results"] else None

def upsert(title, xml, parent_id, existing=None):
    body = {"type": "page", "title": title, "space": {"key": SPACE},
            "body": {"storage": {"value": xml, "representation": "storage"}}}
    if parent_id:
        body["ancestors"] = [{"id": parent_id}]
    existing = existing or find_page(title)
    if existing:
        body["version"] = {"number": existing["version"]["number"] + 1}
        st, d = req("PUT", f"/rest/api/content/{existing['id']}", body)
    else:
        st, d = req("POST", "/rest/api/content", body)
    if st != 200:
        fail(f"save failed for {title!r} ({st})", d)
    return d["id"]

def label(page_id, names):
    st, d = req("POST", f"/rest/api/content/{page_id}/label", [{"prefix": "global", "name": n} for n in names])
    if st != 200:
        print(f"  label failed ({st}): {str(d)[:120]}")

def render_errors(page_id):
    st, d = req("GET", f"/rest/api/content/{page_id}?expand=body.view")
    view = re.sub(r"<script.*?</script>", "", d["body"]["view"]["value"], flags=re.S)
    return re.findall(r"(Unknown macro[^<]*|Error rendering macro[^<]*|Unable to render[^<]*|can only be used[^<]*|must be used[^<]*|broken\.[a-z]+)", view)

def space_template(name, xml, labels, description):
    """Register as a space page template so it shows in Create > templates."""
    body = {"name": name, "templateType": "page", "space": {"key": SPACE}, "description": description,
            "labels": [{"prefix": "global", "name": n} for n in labels],
            "body": {"storage": {"value": xml, "representation": "storage"}}}
    st, d = req("GET", f"/rest/experimental/template/page?spaceKey={SPACE}&limit=200")
    existing = next((t for t in d.get("results", []) if t["name"] == name), None) if st == 200 else None
    if existing:
        body["templateId"] = existing["templateId"]
        st, d = req("PUT", "/rest/experimental/template", body)
    else:
        st, d = req("POST", "/rest/experimental/template", body)
    return st, d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default=os.path.join(HERE, "pages"))
    ap.add_argument("--parent", help="parent page id (default: the space home page)")
    ap.add_argument("--space-templates", action="store_true", help="also register each page as a space template")
    ap.add_argument("--check", action="store_true", help="only report rendering errors on the published pages")
    a = ap.parse_args()

    manifest = json.load(open(os.path.join(a.pages, "manifest.json")))
    user_key = os.environ.get("USER_KEY") or req("GET", "/rest/api/user/current")[1]["userKey"]
    applink = os.environ.get("JIRA_APPLINK_ID")
    if not applink:
        st, d = req("GET", "/rest/applinks/1.0/applicationlink")
        links = d.get("applicationLinks", []) if st == 200 else []
        applink = next((l["id"] for l in links if l.get("isPrimary")), links[0]["id"] if links else None)

    def fill(xml):
        xml = xml.replace("{{USER_KEY}}", user_key)
        if applink:
            return xml.replace("{{JIRA_APPLINK_ID}}", applink)
        return xml.replace('<ac:parameter ac:name="serverId">{{JIRA_APPLINK_ID}}</ac:parameter>', "")

    st, d = req("GET", f"/rest/api/space/{SPACE}?expand=homepage")
    if st != 200:
        fail(f"space {SPACE} not found", d)
    home_id = d["homepage"]["id"]
    parent = a.parent or home_id

    if a.check:
        for e in manifest["pages"]:
            pg = find_page(e["title"])
            errs = render_errors(pg["id"]) if pg else ["not published"]
            print(f"{'ERR ' if errs else 'ok  '} {e['title']}" + (f": {errs}" if errs else ""))
        return

    # Home page body
    hx = fill(open(os.path.join(a.pages, manifest["home"])).read())
    st, home = req("GET", f"/rest/api/content/{home_id}?expand=version")
    st, d = req("PUT", f"/rest/api/content/{home_id}", {"type": "page", "title": home["title"], "space": {"key": SPACE},
            "version": {"number": home["version"]["number"] + 1}, "body": {"storage": {"value": hx, "representation": "storage"}}})
    if st != 200:
        fail("home page update failed", d)
    print(f"home  {home['title']}  {BASE}/pages/viewpage.action?pageId={home_id}")

    for e in manifest["pages"]:
        xml = fill(open(os.path.join(a.pages, e["file"])).read())
        pid = upsert(e["title"], xml, parent)
        label(pid, e["labels"])
        errs = render_errors(pid)
        print(f"{'ERR ' if errs else 'page'}  {e['title']}  {BASE}/pages/viewpage.action?pageId={pid}" + (f"  {errs}" if errs else ""))
        if a.space_templates:
            st, d = space_template(e["title"], xml, e["labels"], f"IT documentation template: {e['title']}")
            print(f"      template {'ok' if st == 200 else 'failed ' + str(st) + ' ' + str(d)[:160]}")

if __name__ == "__main__":
    main()
