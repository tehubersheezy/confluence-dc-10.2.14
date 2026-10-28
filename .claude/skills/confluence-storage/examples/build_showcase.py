"""Build the Infrastructure Maintenance Hub showcase (hub page + three child runbooks).

Publish:  CONFLUENCE_URL=http://localhost:8095 CONFLUENCE_PAT=... SPACE_KEY=TEST \
          USER_KEY=<userKey> JIRA_APPLINK_ID=<applink id> python3 build_showcase.py
Dry run:  python3 build_showcase.py --out DIR   (writes the storage XML with {{placeholders}}, no API calls)
"""
import json, os, re, sys, urllib.request, urllib.parse
OUT = sys.argv[sys.argv.index("--out")+1] if "--out" in sys.argv else None
B=os.environ.get("CONFLUENCE_URL","http://localhost:8095")
H={"Authorization":"Bearer "+os.environ.get("CONFLUENCE_PAT",""),"Content-Type":"application/json"}
SPACE=os.environ.get("SPACE_KEY","TEST") if not OUT else "{{SPACE_KEY}}"
UK=os.environ.get("USER_KEY","{{USER_KEY}}") if not OUT else "{{USER_KEY}}"
SID=os.environ.get("JIRA_APPLINK_ID","{{JIRA_APPLINK_ID}}") if not OUT else "{{JIRA_APPLINK_ID}}"
def req(m,p,b=None):
    r=urllib.request.Request(B+p,data=json.dumps(b).encode() if b is not None else None,method=m,headers=H)
    try:
        with urllib.request.urlopen(r) as x: return x.status,json.loads(x.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code,e.read().decode()[:400]

# --- builders ---
def M(n,params=None,rich=None):
    p="".join(f'<ac:parameter ac:name="{k}">{v}</ac:parameter>' for k,v in (params or {}).items())
    b=f'<ac:rich-text-body>{rich}</ac:rich-text-body>' if rich is not None else ""
    return f'<ac:structured-macro ac:name="{n}">{p}{b}</ac:structured-macro>'
def status(t,c,subtle=False): return M("status",{"colour":c,"title":t,**({"subtle":"true"} if subtle else {})})
USER=f'<ac:link><ri:user ri:userkey="{UK}"/></ac:link>'
def date(d): return f'<time datetime="{d}"/>'
def page(t): return f'<ac:link><ri:page ri:content-title="{t}"/></ac:link>'
def jira_key(k): return M("jira",{"serverId":SID,"key":k,"showSummary":"true"})
def section(kind,*cells): return f'<ac:layout-section ac:type="{kind}">'+"".join(f"<ac:layout-cell>{c}</ac:layout-cell>" for c in cells)+"</ac:layout-section>"
def details(rows,label_id=None):
    tr="".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k,v in rows)
    return M("details",{"id":label_id} if label_id else {},f"<table><tbody>{tr}</tbody></table>")
def tasks(items):
    return "<ac:task-list>"+"".join(f'<ac:task><ac:task-id>{i}</ac:task-id><ac:task-status>{"complete" if done else "incomplete"}</ac:task-status><ac:task-body>{body}</ac:task-body></ac:task>' for i,(done,body) in enumerate(items,1))+"</ac:task-list>"

def slug(t): return re.sub(r"[^a-z0-9]+","-",t.lower()).strip("-")
def upsert(title,body,parent=None,labels=()):
    if OUT:
        open(os.path.join(OUT,slug(title)+".xml"),"w").write(body); return "PARENT"
    st,d=req("GET","/rest/api/content?spaceKey="+SPACE+"&title="+urllib.parse.quote(title)+"&expand=version")
    payload={"type":"page","title":title,"space":{"key":SPACE},"body":{"storage":{"value":body,"representation":"storage"}}}
    if parent: payload["ancestors"]=[{"id":parent}]
    if d["results"]:
        pid=d["results"][0]["id"]; payload["version"]={"number":d["results"][0]["version"]["number"]+1}
        st,r=req("PUT",f"/rest/api/content/{pid}",payload)
    else:
        st,r=req("POST","/rest/api/content",payload)
    if st!=200: print("FAIL",title,st,r); sys.exit(1)
    if labels: req("POST",f"/rest/api/content/{r['id']}/label",[{"prefix":"global","name":l} for l in labels])
    print("ok",title,r["id"]); return r["id"]

# --- hub ---
hub_title="Infrastructure Maintenance Hub · November 2026"
hub_placeholder=upsert(hub_title,"<p>…</p>",labels=("infra","maintenance"))

runbooks=[
 ("Runbook: TLS certificate rotation","ASDF-1","Rotate the wildcard and internal service certificates before the November 30 expiry.","45 min","Green","LOW",
  [(True,"Request new wildcard certificate from the CA"),(False,f"Stage certificates on the load balancers {date('2026-11-12')}"),(False,"Swap listeners during the window and verify the TLS handshake")]),
 ("Runbook: Postgres 16.4 patch","ASDF-2","Apply the 16.4 minor release to the primary and both replicas with a rolling restart.","90 min","Yellow","MEDIUM",
  [(True,"Take a verified base backup"),(False,f"Patch replicas one at a time {date('2026-11-14')}"),(False,"Fail over, patch the old primary, fail back")]),
 ("Runbook: Confluence upgrade check","ASDF-3","Validate macros, application links, and storage-format pages after the platform update.","30 min","Green","LOW",
  [(False,"Re-run the storage format test pages"),(False,"Confirm the Jira application link reports as working")]),
]
for t,key,summary,dur,colour,risk,steps in runbooks:
    body=(M("excerpt",{"hidden":"false"},f"<p>{summary}</p>")
      + details([("Owner",USER),("Duration",dur),("Risk",status(risk,colour)),("Jira",jira_key(key))])
      + "<h2>Steps</h2>"+tasks(steps)
      + M("note",{"title":"Rollback"},"<p>Every step is reversible. If verification fails, stop and follow the rollback section on the hub page.</p>"))
    upsert(t,body,parent=hub_placeholder,labels=("infra-runbook",))

H2=lambda t,anchor=None: (M("anchor",{"":anchor}) if anchor else "")+f"<h2>{t}</h2>"
hero = (M("info",{"title":"Maintenance window: Saturday, November 14 · 22:00–02:00 ET"},
          f"<p>Three changes ship in one window. Customer-facing services stay up; internal tools may be briefly read-only. "
          f"Overall status {status('ON TRACK','Green')} {status('CAB APPROVED','Blue')}</p>"))
overview = (H2("Overview","overview")
  + M("excerpt",{},"<p>A single coordinated window to rotate TLS certificates, patch the Postgres fleet, and verify Confluence after its platform update — with a tested rollback for each change.</p>")
  + "<p>Each change has its own runbook below. Owners update their task list during the window, and the Jira table refreshes live, so this page is the single place to check progress.</p>"
  + "<h3>Goals</h3><ul><li>Zero customer-facing downtime</li><li>Every change verified before the next one starts</li><li>Rollback available within 15 minutes at every step</li></ul>")
sidebar = (M("panel",{"title":"On this page","borderStyle":"solid"}, M("toc",{"maxLevel":"2","minLevel":"2","style":"none"}))
  + details([("Change owner",USER),("Window",f"{date('2026-11-14')} 22:00–02:00 ET"),("Status",status("ON TRACK","Green")),("Risk",status("MEDIUM","Yellow")),("Change ticket",jira_key("ASDF-1"))]))
def card(title,colour,txt,key,st):
    return M("panel",{"title":title,"titleBGColor":colour,"titleColor":"#FFFFFF","borderColor":colour,"borderStyle":"solid"},
             f"<p>{st}</p><p>{txt}</p>{jira_key(key)}")
cards=[card("Certificates","#0052CC","Wildcard and internal certificates, staged on the load balancers.","ASDF-1",status("READY","Green")),
       card("Database","#FF991F","Rolling patch of the primary and two replicas to 16.4.","ASDF-2",status("NEEDS REVIEW","Yellow")),
       card("Confluence","#6554C0","Post-update check of macros and the Jira link.","ASDF-3",status("SCHEDULED","Blue"))]
workitems = (H2("Work items","work") + M("jira",{"serverId":SID,"jqlQuery":"project = ASDF ORDER BY status ASC, key ASC","columns":"type,key,summary,status,assignee,updated","maximumIssues":"20"}))
charts_left = ("<h3>Issues by status</h3>"+M("jirachart",{"serverId":SID,"jql":"project = ASDF","chartType":"pie","statType":"statuses"}))
chart_table = "<table><tbody><tr><th>Team</th><th>Prep</th><th>Window</th></tr><tr><td>Networking</td><td>3</td><td>1</td></tr><tr><td>Data</td><td>5</td><td>2</td></tr><tr><td>Platform</td><td>2</td><td>1</td></tr></tbody></table>"
charts_right = ("<h3>Planned hours by team</h3>"+M("chart",{"type":"bar","stacked":"true","width":"420","height":"300","legend":"true","dataOrientation":"vertical","colors":"#0052CC,#00B8D9","yLabel":"Hours"},chart_table))
runbook_section = (H2("Runbooks","runbooks")
  + M("detailssummary",{"cql":'label = &quot;infra-runbook&quot; and space = currentSpace()',"headings":"Owner,Duration,Risk,Jira","firstcolumn":"Runbook","sortBy":"Risk"})
  + "<h3>Summaries</h3>" + M("children",{"excerptType":"simple","sort":"title"}))
checklist = (H2("Window checklist","checklist") + tasks([
    (True,f"CAB approval recorded {USER}"),
    (True,"Status page notice drafted"),
    (False,f"Announce the window in #ops {date('2026-11-13')}"),
    (False,f"Confirm backups are verified {USER} {date('2026-11-14')}"),
    (False,"Post the all-clear and close the change")]))
guidance = (H2("Before you start","before")
  + M("warning",{"title":"Stop conditions"},"<p>Halt the window if replication lag exceeds 30 seconds or error rates double for five minutes.</p>")
  + M("tip",{"title":"Bridge"},"<p>Join the maintenance bridge 15 minutes early. The incident commander calls each go/no-go.</p>"))
rollback = (H2("Rollback plans","rollback")
  + M("expand",{"title":"Certificates — restore the previous listener"},"<ol><li>Reattach the previous certificate to each listener.</li><li>Confirm the old fingerprint from a client.</li><li>Record the rollback on ASDF-1.</li></ol>")
  + M("expand",{"title":"Database — fail back to the unpatched primary"},"<ol><li>Promote the unpatched replica.</li><li>Repoint the connection pooler.</li><li>Rebuild the patched node from the base backup.</li></ol>")
  + M("expand",{"title":"Confluence — revert the configuration change"},"<ol><li>Restore the saved configuration.</li><li>Restart the node.</li><li>Re-run the storage format checks.</li></ol>"))
related = ("<h3>Related pages</h3>"+M("contentbylabel",{"cql":'label in (&quot;infra&quot;,&quot;infra-runbook&quot;) and space = currentSpace()',"max":"6","showLabels":"false","showSpace":"false","excludeCurrent":"true"}).replace('ac:name="contentbylabel"','ac:name="contentbylabel" ac:schema-version="3"'))
activity = ("<h3>Recent activity</h3>"+M("recently-updated",{"spaces":'<ri:space ri:space-key="'+SPACE+'"/>',"labels":"infra-runbook","max":"5","theme":"concise","hideHeading":"true"}))
people = ("<h3>Contacts</h3>"+M("profile",{"user":f'<ri:user ri:userkey="{UK}"/>'}))
footer = (f'<p style="text-align: center;">{M("status",{"colour":"Grey","title":"LAST REVIEWED","subtle":"true"})} {date("2026-10-27")} · '
          f'<ac:link ac:anchor="overview"><ac:plain-text-link-body><![CDATA[Back to top]]></ac:plain-text-link-body></ac:link></p>')

body = "<ac:layout>" + "".join([
  section("single", hero),
  section("two_right_sidebar", overview, sidebar),
  section("three_equal", *cards),
  section("single", workitems),
  section("two_equal", charts_left, charts_right),
  section("single", runbook_section),
  section("two_equal", checklist, guidance),
  section("single", rollback),
  section("three_equal", related, activity, people),
  section("single", "<hr/>"+footer),
]) + "</ac:layout>"
hub=upsert(hub_title,body,labels=("infra","maintenance"))
if not OUT: print("URL", f"{B}/pages/viewpage.action?pageId={hub}")
