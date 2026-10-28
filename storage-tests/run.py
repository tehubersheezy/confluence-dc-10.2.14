import json, os, re, sys, urllib.request, urllib.parse, base64, uuid
B = "http://localhost:8095"
H = {"Authorization": "Bearer " + os.environ["CONFLUENCE_PAT"], "Content-Type": "application/json", "X-Atlassian-Token": "no-check"}
UK = "2c968083a18055a401a180562cfe0000"

def req(method, path, body=None, headers=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(B + path, data=data, method=method, headers=headers or H)
    try:
        with urllib.request.urlopen(r) as resp: return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:600]

def page(title, storage, parent=None):
    b = {"type": "page", "title": title, "space": {"key": "TEST"}, "body": {"storage": {"value": storage, "representation": "storage"}}}
    if parent: b["ancestors"] = [{"id": parent}]
    s, d = req("POST", "/rest/api/content", b)
    if s != 200: print("CREATE FAIL", title, s, d); sys.exit(1)
    return d["id"]

def attach(pid, name, ctype, content):
    bd = uuid.uuid4().hex
    body = (f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode() + content + f"\r\n--{bd}--\r\n".encode()
    h = {"Authorization": H["Authorization"], "X-Atlassian-Token": "no-check", "Content-Type": f"multipart/form-data; boundary={bd}"}
    s, d = req("POST", f"/rest/api/content/{pid}/child/attachment", headers=h, raw=body)
    print("attach", name, s)

snips = json.load(open(sys.argv[1]))
root = page("Storage Test Root", "<p>root</p>")
page("Install Guide", "<p>install</p>", root)
page("Shared Footer", '<ac:structured-macro ac:name="excerpt"><ac:rich-text-body><p>FOOTER-EXCERPT</p></ac:rich-text-body></ac:structured-macro><p>FOOTER-BODY</p>', root)
labelled = page("Labelled Doc", '<ac:structured-macro ac:name="details"><ac:rich-text-body><table><tbody><tr><th>Owner</th><td>Abey</td></tr><tr><th>Status</th><td>Draft</td></tr></tbody></table></ac:rich-text-body></ac:structured-macro>', root)
req("POST", f"/rest/api/content/{labelled}/label", [{"prefix": "global", "name": "project-doc"}])
target = page("Macro Test", "<p>placeholder</p>", root)
png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
attach(target, "diagram.png", "image/png", png)
attach(target, "spec.pdf", "application/pdf", b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")

results = {}
for name, s in snips.items():
    s = s.replace("USERKEY", UK)
    st, d = req("POST", f"/rest/api/contentbody/convert/view?contentIdContext={target}", {"value": s, "representation": "storage"})
    results[name] = (st, d["value"] if st == 200 else d)
json.dump(results, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w"), indent=1)

# Full page with everything, saved and read back
allv = "".join(v.replace("USERKEY", UK) for k, v in snips.items() if k != "layout") 
s, cur = req("GET", f"/rest/api/content/{target}")
s, d = req("PUT", f"/rest/api/content/{target}", {"type": "page", "title": "Macro Test", "version": {"number": cur["version"]["number"] + 1}, "body": {"storage": {"value": allv, "representation": "storage"}}})
print("full page save", s, d if s != 200 else "")
lay = page("Layout Test", snips["layout"], root)
s, d = req("GET", f"/rest/api/content/{lay}?expand=body.storage")
print("layout readback ok:", "ac:layout-section" in d["body"]["storage"]["value"])
print("target", target)
