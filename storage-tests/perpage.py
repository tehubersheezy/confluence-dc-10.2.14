import json, os, re, sys, html, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
B="http://localhost:8095"; H={"Authorization":"Bearer "+os.environ["CONFLUENCE_PAT"],"Content-Type":"application/json"}
UK="2c968083a18055a401a180562cfe0000"; ROOT=sys.argv[2]; MT=sys.argv[3]
def req(m,p,b=None):
    r=urllib.request.Request(B+p,data=json.dumps(b).encode() if b is not None else None,method=m,headers=H)
    try:
        with urllib.request.urlopen(r) as x: return x.status,json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code,e.read().decode()
snips=json.load(open(sys.argv[1])); only=sys.argv[4:] 
out={}
for k,v in snips.items():
    if only and k not in only: continue
    v=v.replace("USERKEY",UK).replace('ri:attachment ri:filename="','ri:attachment ri:filename="') 
    st,d=req("POST","/rest/api/content",{"type":"page","title":os.environ.get("PFX","S: ")+k,"space":{"key":"TEST"},"ancestors":[{"id":ROOT}],"body":{"storage":{"value":v,"representation":"storage"}}})
    if st!=200:
        m=re.search(r'"message":"([^"]{0,160})',d); out[k]=("SAVE-FAIL %s %s"%(st,m.group(1) if m else d[:160]),""); continue
    pid=d['id']
    if k.startswith("att-"):
        import subprocess
        for f in [os.path.join(HERE,f) for f in ("diagram.png","spec.pdf","book.xlsx","deck.pptx")]:
            subprocess.run(["curl","-s","-o","/dev/null","-H","Authorization: "+H["Authorization"],"-H","X-Atlassian-Token: no-check","-F","file=@"+f,f"{B}/rest/api/content/{pid}/child/attachment"])
    st,d=req("GET",f"/rest/api/content/{pid}?expand=body.view,body.storage")
    out[k]=(d["body"]["view"]["value"], d["body"]["storage"]["value"])
json.dump(out,open(os.path.join(HERE,"perpage.json"),"w"),indent=1)
for k,(view,stor) in out.items():
    if view.startswith("SAVE-FAIL"): print("##",k,view); continue
    t=re.sub(r'<script.*?</script>','',view,flags=re.S)
    err=re.search(r'(Unknown macro[^<]*|Error rendering macro[^<]*|Unable to render[^<]*|can only be used[^<]*|broken\.[a-z]+|must be used[^<]*)',t)
    print("##",k,"ERR: "+err.group(0) if err else "", "|", re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t))).strip()[:160])
