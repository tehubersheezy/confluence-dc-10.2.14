#!/usr/bin/env python3
"""Build the IT documentation templates as Confluence storage-format XML.

    python3 templates/build.py            # writes templates/pages/*.xml
    python3 templates/build.py --out DIR  # writes somewhere else

Every page shares one design: a grey header band with the summary and status
lozenges, an optional row of accent-coloured stat cards, then a two-column body
with the content on the left and a sidebar holding the table of contents, the
page properties, and a collapsed "About this template" note.

Placeholders `{{USER_KEY}}` and `{{JIRA_APPLINK_ID}}` are filled in by publish.py.
"""
import argparse, os, sys, xml.etree.ElementTree as ET

TODAY = "2026-10-28"
USER = '<ac:link><ri:user ri:userkey="{{USER_KEY}}"/></ac:link>'

# Atlassian palette, used for card titles. One accent per document family.
BLUE, GREEN, ORANGE, RED, PURPLE, TEAL, NEUTRAL = (
    "#0052CC", "#00875A", "#FF991F", "#DE350B", "#6554C0", "#00A3BF", "#42526E")
BAND_BORDER = "#DFE1E6"

# Example Jira references. Keys that exist on the target Jira render as live issue lozenges.
JIRA_KEY, JIRA_PROJECT = "ASDF-1", "ASDF"

# ----------------------------------------------------------------- helpers

def ph(text):
    """A placeholder the author replaces."""
    return f"<em>[{text}]</em>"

def p(*inline):
    return "<p>" + "".join(inline) + "</p>"

def h2(t): return f"<h2>{t}</h2>"
def h3(t): return f"<h3>{t}</h3>"

def ul(*items): return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
def ol(*items): return "<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>"

def status(title, colour="Grey", subtle=False):
    s = f'<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">{colour}</ac:parameter><ac:parameter ac:name="title">{title}</ac:parameter>'
    if subtle:
        s += '<ac:parameter ac:name="subtle">true</ac:parameter>'
    return s + "</ac:structured-macro>"

def date(d=TODAY): return f'<time datetime="{d}"/>'

def link(title, text=None):
    body = f"<ac:plain-text-link-body><![CDATA[{text}]]></ac:plain-text-link-body>" if text else ""
    return f'<ac:link><ri:page ri:content-title="{title}"/>{body}</ac:link>'

def anchor_link(name, text):
    return f'<ac:link ac:anchor="{name}"><ac:plain-text-link-body><![CDATA[{text}]]></ac:plain-text-link-body></ac:link>'

def anchor(name):
    return f'<ac:structured-macro ac:name="anchor"><ac:parameter ac:name="">{name}</ac:parameter></ac:structured-macro>'

def image(filename, width=700):
    return f'<ac:image ac:width="{width}"><ri:attachment ri:filename="{filename}"/></ac:image>'

def table(headers, rows):
    out = ["<table><tbody>"]
    if headers:
        out.append("<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)

def kv_table(rows):
    """Two-column key/value table with the key as a header cell."""
    return "<table><tbody>" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</tbody></table>"

def macro(name, body=None, plain=False, **params):
    out = [f'<ac:structured-macro ac:name="{name}">']
    for k, v in params.items():
        k = "" if k == "default" else k
        out.append(f'<ac:parameter ac:name="{k}">{v}</ac:parameter>')
    if body is not None:
        if plain:
            out.append(f"<ac:plain-text-body><![CDATA[{body}]]></ac:plain-text-body>")
        else:
            out.append(f"<ac:rich-text-body>{body}</ac:rich-text-body>")
    out.append("</ac:structured-macro>")
    return "".join(out)

def code(body, language="bash", title=None):
    params = {"language": language}
    if title:
        params["title"] = title
    return macro("code", body, plain=True, **params)

def callout(kind, body, title=None):
    """kind: info | tip | note | warning"""
    return macro(kind, body, **({"title": title} if title else {}))

def expand(title, body): return macro("expand", body, title=title)

def panel(body, title=None, bg=None, border=None, title_bg=None):
    params = {}
    if title: params["title"] = title
    if bg: params["bgColor"] = bg
    params["borderStyle"] = "solid"
    params["borderColor"] = border or BAND_BORDER
    if title_bg:
        params["titleBGColor"] = title_bg
        params["titleColor"] = "#FFFFFF"
    return macro("panel", body, **params)

def card(title, colour, body):
    return panel(body, title=title, title_bg=colour, border=colour)

def tasks(items, start=1):
    out = ["<ac:task-list>"]
    for i, body in enumerate(items, start):
        out.append(f"<ac:task><ac:task-id>{i}</ac:task-id><ac:task-status>incomplete</ac:task-status><ac:task-body>{body}</ac:task-body></ac:task>")
    out.append("</ac:task-list>")
    return "".join(out)

def assigned(text, due):
    return f"{USER} {text} {date(due)}"

def jira_issue(key):
    return macro("jira", serverId="{{JIRA_APPLINK_ID}}", key=key, showSummary="true")

def report(cql, headings, first="Page"):
    return macro("detailssummary", cql=cql, headings=headings, firstcolumn=first)

def section(kind, *cells):
    return f'<ac:layout-section ac:type="{kind}">' + "".join(f"<ac:layout-cell>{c}</ac:layout-cell>" for c in cells) + "</ac:layout-section>"

def page(doc_type, summary, lozenges, props, body, about, cards=None):
    """Assemble a full page from its parts."""
    band = panel(
        macro("excerpt", p("<strong>", summary, "</strong>"), hidden="false")
        + p(status(doc_type.upper(), "Grey", subtle=True), " ", " ".join(lozenges)))
    sidebar = (
        panel(macro("toc", minLevel="2", maxLevel="2", style="none", indent="0px"), title="On this page")
        + macro("details", kv_table([("Document type", doc_type)] + props))
        + expand("About this template", p(about, " Delete this box when the page is done."))
    )
    sections = [section("single", band)]
    if cards:
        sections.append(section("three_equal", *cards))
    sections.append(section("two_right_sidebar", body, sidebar))
    return "<ac:layout>" + "".join(sections) + "</ac:layout>"

def std_props(status_title="DRAFT", status_colour="Grey"):
    return [("Owner", USER), ("Status", status(status_title, status_colour)), ("Last reviewed", date())]

# ----------------------------------------------------------------- templates
# Each returns (title, labels, storage xml). Order here is the order in the space.

def service_overview():
    body = (
        h2("What it does") + p(ph("Two or three sentences. What problem it solves, and what it is not responsible for."))
        + h2("Who uses it") + ul(ph("Consumer or team") + " for " + ph("purpose"), ph("Consumer or team") + " for " + ph("purpose"))
        + h2("Quick links") + kv_table([
            ("Source", f'<a href="https://example.com/repo">{ph("Repository")}</a>'),
            ("Dashboards", f'<a href="https://example.com/dashboard">{ph("Health dashboard")}</a>'),
            ("Alerts", f'<a href="https://example.com/alerts">{ph("Alert rules")}</a>'),
            ("Runbooks", link("Runbook")), ("Architecture", link("Architecture Overview")),
            ("Tickets", ph("Jira project or ServiceNow assignment group"))])
        + h2("Architecture at a glance") + p(ph("One diagram. Attach it to this page, or link to the Architecture Overview.")) + image("architecture.png")
        + h2("Dependencies") + table(["Direction", "System", "Purpose", "Failure impact"], [
            ["Upstream", ph("System"), ph("What we get from it"), ph("What breaks if it is down")],
            ["Downstream", ph("System"), ph("What it gets from us"), ph("What breaks for them")]])
        + h2("Environments") + table(["Environment", "URL", "Hosts", "Notes"], [
            ["Production", ph("URL"), ph("Hostnames or cluster"), ph("Change window, approvals")],
            ["Staging", ph("URL"), ph("Hostnames or cluster"), ph("Refresh cadence")],
            ["Development", ph("URL"), ph("Hostnames or cluster"), ""]])
        + h2("Service levels") + table(["Objective", "Target", "Measured by"], [
            ["Availability", ph("99.9%"), ph("Dashboard or alert")],
            ["Latency", ph("p95 under 300 ms"), ph("Dashboard or alert")],
            ["Support response", ph("Within 1 business hour"), ph("Ticket queue report")]])
        + h2("Related pages") + macro("children", all="true")
    )
    cards = [
        card("Owner", GREEN, p(USER) + p(ph("Team"))),
        card("On-call", GREEN, p(ph("Rotation name")) + p(ph("Support channel"))),
        card("Tier", GREEN, p(status("TIER 1", "Red")) + p(ph("Why it has this tier"))),
    ]
    props = std_props() + [("Team", ph("Owning team")), ("Tier", status("TIER 1", "Red")), ("Support channel", ph("#channel or queue"))]
    return ("Service Overview", ["service-overview"], page(
        "Service Overview", ph("One sentence: what this service does and who depends on it."),
        [status("DRAFT"), status("TIER 1", "Red")], props, body,
        "The front door for a service. Keep it to one screen and link out to runbooks, dashboards, and design docs rather than copying them here.", cards))

def architecture_overview():
    body = (
        h2("Purpose and scope") + p(ph("What the system is for and what this document covers. Name what is out of scope."))
        + h2("Quality goals") + table(["Priority", "Goal", "How it shapes the design"], [
            ["1", ph("Availability"), ph("Active-active across two sites")],
            ["2", ph("Auditability"), ph("Append-only event log")],
            ["3", ph("Cost"), ph("Shared database tier")]])
        + h2("System context") + p(ph("Diagram: the system as one box, the people who use it, and the external systems it talks to.")) + image("context.png")
        + table(["Actor or system", "Role", "Interaction"], [
            [ph("End user"), ph("Who they are"), ph("What they do through the system")],
            [ph("Identity provider"), "External system", ph("SAML login")]])
        + h2("Containers") + p(ph("Diagram: the deployable units. One box per thing that runs as its own process.")) + image("containers.png")
        + table(["Container", "Technology", "Responsibility", "Runs on"], [
            [ph("Web app"), ph("Java 21, Spring"), ph("Serves UI and API"), ph("k8s cluster prod-east")],
            [ph("Database"), ph("PostgreSQL 16"), ph("System of record"), ph("RDS, Multi-AZ")],
            [ph("Queue"), ph("RabbitMQ"), ph("Async jobs"), ph("VM pair")]])
        + h2("Components") + p(ph("Optional. Only for containers whose internals matter to other teams."))
        + expand("[Container name] components", table(["Component", "Responsibility", "Depends on"], [[ph("Auth module"), ph("Token validation"), ph("Identity provider")]]))
        + h2("Key data flows") + p(ph("The two or three flows that explain how the system works."))
        + h3(ph("Flow name, for example: user submits a request")) + ol(ph("Step"), ph("Step"), ph("Step"))
        + h2("Cross-cutting concerns") + kv_table([
            ("Authentication and authorization", ph("SSO via SAML, roles from AD groups")),
            ("Secrets", ph("Vault, rotated every 90 days")),
            ("Logging and monitoring", ph("Logs to Splunk, metrics to Prometheus, dashboard link")),
            ("Backup and recovery", ph("Nightly snapshots, RPO 24 h, RTO 4 h")),
            ("Network and security zones", ph("DMZ for web tier, internal for data tier"))])
        + h2("Environments and deployment") + p(ph("How code gets to production, how environments differ, where infrastructure is defined."))
        + h2("Decisions") + p("Significant decisions are recorded as ADRs and listed here automatically.")
        + report('label = "adr" and space = currentSpace()', "Status,Decision date,Owner", "Decision")
        + h2("Risks and technical debt") + table(["Risk", "Impact", "Mitigation or plan"], [[ph("Single queue node"), ph("Outage on failure"), ph("Cluster in Q1, see ADR-7")]])
    )
    props = std_props() + [("System", ph("System name")), ("Architect", ph("Name"))]
    return ("Architecture Overview", ["architecture"], page(
        "Architecture Overview", ph("One sentence: the system this describes and the boundary it covers."),
        [status("DRAFT")], props, body,
        "Follows the C4 model: context, containers, components. Stop at the level that is useful; most systems need the first two plus data flows. Record decisions as ADRs and link them rather than explaining them inline."))

def adr():
    body = (
        h2("Context") + p(ph("The situation that forces a decision. Constraints, requirements, and what happens if nothing changes. Facts only, no argument yet."))
        + h2("Decision") + p(ph('What we are doing, in the active voice: "We will…" Include the scope: which systems, teams, or timeframes it applies to.'))
        + h2("Alternatives considered") + table(["Option", "Pros", "Cons", "Why not chosen"], [
            [ph("Option A, the chosen one"), ph("Pros"), ph("Cons"), "Chosen"],
            [ph("Option B"), ph("Pros"), ph("Cons"), ph("Reason")],
            ["Do nothing", ph("No work"), ph("Problem persists"), ph("Reason")]])
        + h2("Consequences")
        + h3("Positive") + ul(ph("What gets easier or better"))
        + h3("Negative") + ul(ph("What gets harder, what we now have to maintain, what we give up"))
        + h3("Neutral") + ul(ph("Changes that are neither, such as a new team convention"))
        + h2("Follow-up actions") + tasks([assigned(ph("Action needed to put the decision into effect"), "2026-11-30")])
        + h2("References") + ul(ph("Design doc, vendor doc, benchmark, ticket"))
    )
    lifecycle = p(status("PROPOSED", "Yellow"), " under review  ", status("ACCEPTED", "Green"), " in effect  ", status("REJECTED", "Red"), " not adopted  ", status("SUPERSEDED", "Grey"), " replaced")
    props = std_props("PROPOSED", "Yellow") + [("Decision date", date()), ("Deciders", ph("Names or group")), ("Supersedes", ph("ADR link or none"))]
    return ("ADR-000: Architecture Decision Record", ["adr"], page(
        "Architecture Decision Record", ph('One sentence: the decision, stated as a fact. "We will use PostgreSQL for the audit store."'),
        [status("PROPOSED", "Yellow")], props, body,
        "Title the page <strong>ADR-NNN: Short decision title</strong>. One decision per page. Never edit an accepted decision; write a new ADR that supersedes it and update the status here. Lifecycle: " + lifecycle))

def design_doc():
    body = (
        h2("Problem") + p(ph("What is wrong or missing today, who it affects, and what it costs. Evidence beats opinion: ticket counts, outage minutes, hours lost."))
        + h2("Goals") + ul(ph("Measurable outcome"), ph("Measurable outcome"))
        + h2("Non-goals") + ul(ph("Things a reader might expect this to cover that it deliberately does not"))
        + h2("Proposed design") + p(ph("Enough detail that a reviewer can find flaws. Start with a diagram, then walk through the main flows. Call out what changes for operators and for users.")) + image("design.png")
        + h3("Components") + p(ph("New or changed components and their responsibilities."))
        + h3("Data model") + p(ph("New tables, fields, schemas, or message formats."))
        + h3("Interfaces") + p(ph("APIs, CLI flags, config options, events. Include an example."))
        + code("# replace with a real example\nkey: value", "yaml", "Example")
        + h3("Security and compliance") + p(ph("Authentication, authorization, data classification, audit, retention. Name the reviewer if a security review is required."))
        + h3("Operations") + p(ph("Monitoring, alerting, backup, capacity, on-call impact. Which runbooks need to be written or changed."))
        + h2("Alternatives considered") + table(["Option", "Summary", "Why not"], [
            [ph("Option"), ph("What it would look like"), ph("Trade-off that ruled it out")],
            ["Do nothing", ph("Current state continues"), ph("Cost of inaction")]])
        + h2("Risks and mitigations") + table(["Risk", "Likelihood", "Impact", "Mitigation"], [[ph("Risk"), ph("Low / Medium / High"), ph("Low / Medium / High"), ph("How we reduce or detect it")]])
        + h2("Rollout plan") + ol(ph("Phase 1: scope, environment, success criteria"), ph("Phase 2"), ph("Rollback trigger and procedure"))
        + h2("Open questions") + tasks([ph("Question, who needs to answer it, and by when")])
        + h2("Review log") + table(["Date", "Reviewer", "Outcome", "Notes"], [[date(), ph("Name"), ph("Approved / Changes requested"), ph("Summary")]])
    )
    cards = [
        card("Problem", TEAL, p(ph("One line: what hurts today"))),
        card("Proposal", TEAL, p(ph("One line: what we will build"))),
        card("Decision needed by", TEAL, p(date("2026-11-15")) + p(ph("Who decides"))),
    ]
    props = std_props() + [("Reviewers", ph("Names")), ("Review by", date("2026-11-15")), ("Target delivery", ph("Quarter or date")), ("Ticket", ph("Epic or change request"))]
    return ("Design Document", ["design-doc"], page(
        "Design Document", ph("One sentence: the problem and the proposed change."),
        [status("DRAFT"), status("REVIEW BY NOV 15", "Blue")], props, body,
        "Write this before the work starts and circulate it for review. Reviewers comment inline; unresolved disagreements go in Open questions. Decisions that will outlive the project get their own ADR once approved.", cards))

def runbook():
    body = (
        h2("When to use this") + p(ph("The exact symptom or event. Link the alert. Say when not to use it and which runbook to use instead."))
        + h2("Prerequisites") + tasks([ph("Access confirmed, for example: can SSH to the host"), ph("Change ticket opened or maintenance window confirmed"), ph("Stakeholders notified in the support channel")])
        + h2("Steps")
        + h3("1. " + ph("Confirm the problem")) + code("systemctl status example.service")
        + p("<strong>Expected:</strong> ", ph("What a healthy or unhealthy result looks like."))
        + h3("2. " + ph("Take the corrective action")) + code("sudo systemctl restart example.service")
        + p("<strong>Expected:</strong> ", ph("Result."))
        + callout("warning", p(ph("Anything irreversible or customer-visible in the next step.")), "Before you continue")
        + h3("3. " + ph("Next step")) + p(ph("Step."))
        + h2("Verification") + tasks([ph("Alert has cleared"), ph("Dashboard shows normal values for 10 minutes"), ph("A test request succeeds end to end")], start=4)
        + h2("Rollback") + p(ph("How to undo each step if verification fails. If a step cannot be undone, say so here and in the warning above."))
        + h2("Escalation") + table(["If", "Contact", "How"], [
            [ph("Verification fails after rollback"), ph("Secondary on-call"), ph("Page via rotation")],
            [ph("Vendor component is involved"), ph("Vendor support"), ph("Portal link, contract number")]])
        + h2("Close out") + ul(ph("Update the ticket with what was done"), ph("Post in the support channel"), ph("If this took more than N minutes or happened twice this month, open a problem record"))
        + h2("History") + table(["Date", "Run by", "Outcome", "Notes"], [[date(), ph("Name"), ph("Resolved / Escalated"), ph("What was different this time")]])
    )
    cards = [
        card("Trigger", BLUE, p(ph("Alert name, ticket type, or schedule"))),
        card("Risk and duration", BLUE, p(status("LOW", "Green"), " ", ph("Typical time to complete"))),
        card("Access needed", BLUE, p(ph("Roles, groups, VPN, bastion"))),
    ]
    props = std_props() + [("Service", link("Service Overview")), ("Risk", status("LOW", "Green")), ("Duration", ph("Typical time")), ("Change approval", ph("Standard change / CAB / none"))]
    return ("Runbook", ["runbook"], page(
        "Runbook", ph("One sentence: what this procedure does and when to run it."),
        [status("DRAFT"), status("LOW RISK", "Green")], props, body,
        "Write for someone paged at 3 a.m. who has never touched this system. Every step is a command or a click with the expected result. If a step needs judgment, say what to look for and what to do in each case.", cards))

def sop():
    body = (
        h2("1. Purpose") + p(ph("Why this procedure exists and what outcome it guarantees."))
        + h2("2. Scope") + p(ph("Which systems, teams, locations, and situations it applies to. Name what is excluded."))
        + h2("3. Roles and responsibilities") + table(["Role", "Responsible for", "Held by"], [
            [ph("Requester"), ph("Submits the request with required details"), ph("Any employee")],
            [ph("Approver"), ph("Reviews and approves within 2 business days"), ph("Service owner")],
            [ph("Executor"), ph("Performs the procedure and records evidence"), ph("Operations team")]])
        + h2("4. Definitions") + table(["Term", "Meaning"], [[ph("Term"), ph("Definition as used in this document")]])
        + h2("5. Policy references") + ul(ph("Policy name and link, for example: Access Control Policy"), ph("Control framework reference, for example: SOX ITGC, ISO 27001 A.9"))
        + h2("6. Procedure")
        + h3("6.1 " + ph("Phase, for example: Request")) + ol(ph("Who does what, in what system, with what inputs"), ph("Step"))
        + h3("6.2 " + ph("Phase, for example: Approval")) + ol(ph("Step"))
        + h3("6.3 " + ph("Phase, for example: Execution")) + ol(ph("Step. Link the technical runbook rather than repeating commands here."))
        + h3("6.4 Exceptions") + p(ph("When the procedure may be bypassed, who can approve that, and how it is recorded."))
        + h2("7. Records and evidence") + table(["Record", "Where kept", "Retention"], [
            [ph("Approval ticket"), ph("ServiceNow"), ph("7 years")],
            [ph("Execution log"), ph("Runbook history table"), ph("2 years")]])
        + h2("8. Metrics") + p(ph("How compliance with this SOP is measured and reported, for example: percentage of requests approved before execution, reviewed monthly."))
        + h2("9. Revision history") + table(["Version", "Date", "Author", "Change", "Approved by"], [["1.0", date(), ph("Name"), "Initial release", ph("Name")]])
    )
    props = std_props() + [("SOP ID", ph("SOP-IT-001")), ("Version", "1.0"), ("Approver", ph("Name, title")), ("Effective date", date("2026-11-01")), ("Review cycle", ph("Annual")), ("Next review", date("2027-11-01"))]
    return ("Standard Operating Procedure", ["sop"], page(
        "Standard Operating Procedure", ph("One sentence: the process this procedure governs."),
        [status("DRAFT"), status("V1.0", "Blue")], props, body,
        "A controlled document: it has an ID, an approver, a review cycle, and a revision history. Use it for processes with compliance or audit weight. For a purely technical procedure, use the Runbook template instead."))

def troubleshooting_guide():
    def symptom(n, name, cause):
        return (anchor(f"symptom-{n}") + h2(f"Symptom {n}: " + ph(name))
            + p("<strong>What you will see:</strong> ", ph("Exact error text, where it appears, which users."))
            + h3("Diagnose") + code("# command that confirms or rules out the cause")
            + p("<strong>If the output shows</strong> ", ph("X"), ", the cause is ", ph(cause), ". Continue below. Otherwise go to ", anchor_link("escalation", "Escalation"), ".")
            + h3("Fix") + ol(ph("Step"), ph("Step"))
            + h3("Confirm") + p(ph("What proves it is fixed."))
            + expand("If that did not work", p(ph("Less common causes with the same symptom, each with a diagnostic and a fix."))))
    body = (
        h2("Quick triage") + table(["Symptom", "Most likely cause", "Go to"], [
            [ph("Users see HTTP 502"), ph("Backend pool unhealthy"), anchor_link("symptom-1", "Symptom 1")],
            [ph("Login loops back to the sign-in page"), ph("Clock skew with the identity provider"), anchor_link("symptom-2", "Symptom 2")],
            [ph("Jobs stuck in queued"), ph("Worker process stopped"), anchor_link("symptom-3", "Symptom 3")]])
        + h2("First five minutes") + p("Run these before anything else. They rule out the common causes.")
        + code("systemctl status example.service\ncurl -sS -o /dev/null -w '%{http_code}\\n' https://example.internal/health\ndf -h /var\njournalctl -u example.service --since '15 min ago' | tail -50", "bash", "Health check")
        + symptom(1, "Users see HTTP 502", "backend pool unhealthy")
        + symptom(2, "Login loops back to the sign-in page", "clock skew")
        + symptom(3, "Jobs stuck in queued", "worker process stopped")
        + h2("Known issues") + table(["Issue", "Workaround", "Tracking"], [[ph("Description"), ph("Temporary fix"), ph("Ticket or vendor case")]])
        + anchor("escalation") + h2("Escalation")
        + p("Before escalating, collect: ", ph("timestamps, affected users, request IDs, the output of the health check above"), ".")
        + table(["Level", "Who", "When"], [
            ["L2", ph("Team or rotation"), ph("Symptom not listed here, or fix failed")],
            ["L3", ph("Engineering owner"), ph("Data loss, security, or more than 30 minutes of impact")],
            ["Vendor", ph("Vendor support"), ph("Fault inside the vendor product")]])
    )
    cards = [
        card("Logs", ORANGE, p(ph("Where logs live, with a link to the search"))),
        card("Dashboard", ORANGE, p(ph("Link to the health dashboard"))),
        card("Escalate to", ORANGE, p(ph("L2 team or rotation"))),
    ]
    props = std_props() + [("Service", link("Service Overview")), ("Logs", ph("Link")), ("Dashboard", ph("Link"))]
    return ("Troubleshooting Guide", ["troubleshooting"], page(
        "Troubleshooting Guide", ph("One sentence: the system this guide covers."),
        [status("DRAFT")], props, body,
        "Organize by symptom, not by component. People arrive with an error message, not a diagnosis. Put the triage table first so they can jump straight to their case. Add a symptom section every time a ticket teaches you something.", cards))

def postmortem():
    body = (
        h2("Summary") + p(ph("Three to five sentences a manager can read on a phone: what happened, the cause, how it was fixed, and what will prevent it."))
        + h2("Impact") + table(["Who", "What they experienced", "Scale"], [
            [ph("Internal users in EMEA"), ph("Could not log in"), ph("About 1,200 users for 105 minutes")],
            [ph("Batch jobs"), ph("Delayed, no data loss"), ph("14 jobs")]])
        + h2("Timeline") + p("All times ", ph("timezone"), ".") + table(["Time", "Event", "Source"], [
            [ph("13:40"), ph("Change deployed: certificate rotation on the load balancer"), ph("Change CHG0012345")],
            [ph("14:02"), ph("First alert: HTTP 5xx rate above 5%"), ph("Monitoring")],
            [ph("14:10"), ph("On-call acknowledged, incident opened"), ph("Incident channel")],
            [ph("14:35"), ph("Cause identified: intermediate certificate missing from the chain"), ph("Incident channel")],
            [ph("15:47"), ph("Fix verified, incident resolved"), ph("Monitoring")]])
        + h2("Root cause") + p(ph('The technical cause in plain terms, then the "why" behind it: why the system allowed it and why the process did not catch it.'))
        + h2("Contributing factors") + ul(ph("Condition that made the incident possible or worse, for example: no staging validation of certificate chains"), ph("Condition"))
        + h2("Detection") + p(ph("How we found out. Monitoring or a user report? How long between the fault and the first alert?"))
        + h2("Response") + p(ph("What slowed or sped up the response: access, documentation, tooling, communication."))
        + h2("What went well") + ul(ph("Something that worked and should be kept"))
        + h2("What went poorly") + ul(ph("Something that failed or was missing"))
        + h2("Where we got lucky") + ul(ph("Something that could have made this much worse but did not, by chance"))
        + h2("Action items") + p("Each item has one owner and a due date. Prevention items come first.")
        + tasks([
            assigned("<strong>Prevent:</strong> " + ph("Add certificate chain check to the deployment pipeline"), "2026-11-15"),
            assigned("<strong>Detect:</strong> " + ph("Alert on TLS handshake failures, not just 5xx rate"), "2026-11-15"),
            assigned("<strong>Mitigate:</strong> " + ph("Write the rollback runbook for load balancer certificate changes"), "2026-11-30")])
        + h2("Lessons learned") + p(ph("What the organization should take from this beyond the action items."))
    )
    cards = [
        card("Severity", RED, p(status("SEV 2", "Red")) + p(ph("Why this severity"))),
        card("Duration", RED, p("<strong>", ph("1 h 45 min"), "</strong>") + p(ph("14:02 to 15:47 ET"))),
        card("Impact", RED, p("<strong>", ph("1,200 users"), "</strong>") + p(ph("Could not log in"))),
    ]
    props = std_props() + [("Incident", jira_issue(JIRA_KEY)), ("Severity", status("SEV 2", "Red")), ("Started", ph("2026-10-27 14:02 ET")), ("Resolved", ph("2026-10-27 15:47 ET")), ("Incident commander", ph("Role or rotation"))]
    return ("Incident Postmortem", ["postmortem"], page(
        "Incident Postmortem", ph("One sentence: what broke, for how long, and who was affected."),
        [status("DRAFT"), status("SEV 2", "Red")], props, body,
        "Blameless. Describe what people knew and did at the time, not what they should have done. Name systems and roles, not individuals. Finish the draft within five business days of resolution and review it with everyone who was on the incident.", cards))

def api_reference():
    body = (
        h2("Authentication") + p(ph("Token type, how to obtain one, where it goes in the request, and how long it lasts."))
        + code('curl -H "Authorization: Bearer $TOKEN" https://api.example.internal/v1/health')
        + h2("Conventions") + kv_table([
            ("Content type", ph("application/json for requests and responses")),
            ("Versioning", ph("Version in the path; breaking changes get a new version; old versions supported for 12 months")),
            ("Pagination", ph("limit and start query parameters; response includes a next link")),
            ("Rate limits", ph("600 requests per minute per token; 429 with Retry-After when exceeded")),
            ("Timestamps", ph("ISO 8601 in UTC")),
            ("Idempotency", ph("PUT and DELETE are idempotent; POST accepts an Idempotency-Key header"))])
        + h2("Endpoints")
        + h3(ph("GET /items")) + p(ph("What it returns and when to use it."))
        + table(["Parameter", "In", "Type", "Required", "Description"], [
            [ph("status"), "query", "string", "No", ph("Filter by status: active, archived")],
            [ph("limit"), "query", "integer", "No", ph("Page size, default 50, max 200")]])
        + code('curl -H "Authorization: Bearer $TOKEN" "https://api.example.internal/v1/items?status=active&limit=2"', "bash", "Request")
        + code('{\n  "results": [\n    {"id": "itm_01", "name": "Example", "status": "active"}\n  ],\n  "next": "/v1/items?status=active&limit=2&start=2"\n}', "json", "Response 200")
        + table(["Status", "Meaning"], [["200", "Success"], ["401", "Missing or expired token"], ["403", "Token lacks the required scope"]])
        + h3(ph("POST /items")) + p(ph("What it creates. Note any side effects."))
        + table(["Field", "Type", "Required", "Description"], [
            [ph("name"), "string", "Yes", ph("Display name, 1 to 100 characters")],
            [ph("status"), "string", "No", ph("Defaults to active")]])
        + code('curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\\n  -d \'{"name": "Example"}\' https://api.example.internal/v1/items', "bash", "Request")
        + code('{"id": "itm_02", "name": "Example", "status": "active"}', "json", "Response 201")
        + h2("Errors") + p("All errors use the same body.")
        + code('{"error": {"code": "validation_failed", "message": "name is required", "details": []}}', "json")
        + table(["Code", "HTTP status", "Meaning", "What to do"], [
            [ph("validation_failed"), "400", ph("Request body failed validation"), ph("Check details for the field")],
            [ph("not_found"), "404", ph("No resource with that ID"), ""],
            [ph("rate_limited"), "429", ph("Too many requests"), ph("Wait for Retry-After seconds")]])
        + h2("Changelog") + table(["Date", "Version", "Change"], [[date(), ph("v1"), ph("Initial release")]])
    )
    props = std_props() + [("API version", ph("v1")), ("Base URL", ph("https://api.example.internal/v1")), ("Spec", ph("Link to OpenAPI document")), ("Support", ph("Channel or queue"))]
    return ("API Reference", ["api-reference"], page(
        "API Reference", ph("One sentence: the API this page documents and its current version."),
        [status("DRAFT"), status("V1", "Blue")], props, body,
        "If the API has an OpenAPI spec, link it in the properties and keep this page to authentication, conventions, and worked examples. Document endpoints by hand only when there is no generated reference. Every endpoint gets one real request and one real response."))

def configuration_reference():
    body = (
        h2("Where configuration lives") + table(["Source", "Path or location", "Managed by", "Precedence"], [
            ["Defaults", ph("Built into the binary"), "Vendor", "Lowest"],
            ["Config file", ph("/etc/example/example.yaml"), ph("Ansible role example"), ""],
            ["Environment variables", ph("Systemd unit drop-in"), ph("Ansible role example"), ""],
            ["Command-line flags", ph("Systemd ExecStart"), ph("Ansible role example"), "Highest"]])
        + callout("warning", p("Edit configuration in ", ph("the source of truth"), ", not on the host. Hand edits are overwritten on the next run."))
        + h2("Options")
        + h3(ph("Section: server")) + table(["Option", "Type", "Default", "Description", "Restart"], [
            [ph("server.port"), "integer", ph("8080"), ph("TCP port to listen on"), "Yes"],
            [ph("server.tls.enabled"), "boolean", ph("false"), ph("Serve HTTPS; requires cert and key"), "Yes"],
            [ph("server.timeout"), "duration", ph("30s"), ph("Request timeout"), "No"]])
        + h3(ph("Section: database")) + table(["Option", "Type", "Default", "Description", "Restart"], [
            [ph("database.url"), "string", "none", ph("JDBC or DSN connection string. Required."), "Yes"],
            [ph("database.pool.max"), "integer", ph("20"), ph("Maximum open connections"), "No"]])
        + h2("Environment variables") + table(["Variable", "Overrides", "Notes"], [
            [ph("EXAMPLE_DB_URL"), ph("database.url"), ph("Keeps the secret out of the file")],
            [ph("EXAMPLE_LOG_LEVEL"), ph("logging.level"), ""]])
        + h2("Secrets") + p(ph("Which values are secrets, where they are stored, how they are injected, and the rotation schedule."))
        + h2("Example configuration")
        + code("server:\n  port: 8443\n  tls:\n    enabled: true\n    cert: /etc/example/tls/server.crt\n    key: /etc/example/tls/server.key\ndatabase:\n  url: ${EXAMPLE_DB_URL}\n  pool:\n    max: 40", "yaml", "Production")
        + h2("Validation and reload") + code("example --config /etc/example/example.yaml --validate\nsudo systemctl reload example.service")
        + h2("Deprecated options") + table(["Option", "Deprecated in", "Removed in", "Replacement"], [[ph("server.ssl"), ph("2.0"), ph("3.0"), ph("server.tls.enabled")]])
    )
    props = std_props() + [("Component", ph("Name and version")), ("Source of truth", ph("Git repo path, Ansible role, vault path"))]
    return ("Configuration Reference", ["configuration"], page(
        "Configuration Reference", ph("One sentence: the component whose configuration this page lists."),
        [status("DRAFT")], props, body,
        "List every option, even the ones nobody changes. The value of a reference is that it is complete. Say where each setting lives, what wins when two sources disagree, and whether a change needs a restart."))

def release_notes():
    body = (
        h2("Highlights") + ul(ph("The one to three changes most people care about"))
        + callout("warning", p(ph("Anything operators or users must do before or after upgrading. Delete this box if there is nothing.")), "Action required")
        + h2("Added") + ul(ph("New capability, with a link to its documentation"))
        + h2("Changed") + ul(ph("Changed behavior. Say what it was before and what it is now."))
        + h2("Deprecated") + ul(ph("Still works but will be removed; give the removal version and the replacement"))
        + h2("Removed") + ul(ph("Feature or option that no longer exists"))
        + h2("Fixed") + ul(ph("Bug fixed, described by symptom"))
        + h2("Security") + ul(ph("Vulnerability addressed, with CVE if public"))
        + h2("Upgrade notes") + ol(ph("Prerequisite, for example: requires database schema version 12"), ph("Step or link to the upgrade runbook"), ph("Rollback: how far back is supported"))
        + h2("Known issues") + table(["Issue", "Workaround", "Tracking"], [[ph("Description"), ph("Workaround"), ph("Ticket")]])
        + h2("Issues in this release") + p(ph("Narrow the query to this release, for example: fixVersion = 2.4.0"))
        + macro("jira", serverId="{{JIRA_APPLINK_ID}}", jqlQuery=f"project = {JIRA_PROJECT} ORDER BY key", columns="key,summary,type,status", maximumIssues="50")
    )
    cards = [
        card("Version", GREEN, p("<strong>", ph("2.4.0"), "</strong>") + p(status("MINOR", "Blue"))),
        card("Release date", GREEN, p("<strong>", date("2026-11-05"), "</strong>") + p(ph("Change ticket"))),
        card("Headline", GREEN, p(ph("The one change most people care about"))),
    ]
    props = std_props() + [("Product", ph("Name")), ("Version", ph("2.4.0")), ("Release date", date("2026-11-05")), ("Release type", status("MINOR", "Blue")), ("Change ticket", ph("CHG number"))]
    return ("Release Notes", ["release-notes"], page(
        "Release Notes", ph("One sentence: the headline of this release."),
        [status("DRAFT"), status("MINOR", "Blue")], props, body,
        "Title the page <strong>[Product] [version] release notes</strong>. Write for the people who run and use the system, not the people who built it. Keep every category heading even when it is empty, and write None.", cards))

def getting_started():
    body = (
        h2("What you will build") + p(ph("The concrete result at the end: a running service, a first deployment, a working query. Show a screenshot or output sample."))
        + h2("Before you begin") + table(["Requirement", "How to check"], [
            [ph("Access to the environment"), ph("You can log in at the URL")],
            [ph("Tool installed, version X or later"), code("example --version")],
            [ph("Time: about 20 minutes"), ""]])
        + h2("Step 1: " + ph("Install")) + p(ph("One action per step. Tell the reader exactly what to type and what they will see."))
        + code("brew install example")
        + p("You should see: ", ph("the last line of successful output"), ".")
        + h2("Step 2: " + ph("Configure")) + p(ph("Keep choices out of a tutorial. Give the one value that works and say where the options are documented."))
        + code("example init --name demo")
        + h2("Step 3: " + ph("Run it")) + code("example run")
        + callout("tip", p(ph("The one thing that trips people up at this step, and how to tell it happened.")), "If it does not start")
        + h2("Check your work") + tasks([ph("The service answers at http://localhost:8080"), ph("The log shows ready"), ph("The dashboard lists the new instance")])
        + h2("Clean up") + p(ph("How to undo everything, if this was a test.")) + code("example destroy --name demo")
        + h2("Next steps") + ul(link("How-to Guide", "How-to guides for common tasks"), link("Configuration Reference", "Full configuration reference"), link("Troubleshooting Guide", "Troubleshooting guide"))
    )
    props = std_props() + [("Audience", ph("Who this is for")), ("Time to complete", ph("20 minutes")), ("Tested on", ph("Version and platform"))]
    return ("Getting Started", ["tutorial"], page(
        "Getting Started", ph("One sentence: what the reader will have working by the end."),
        [status("DRAFT"), status("20 MIN", "Blue")], props, body,
        "A tutorial is a guided path to one working result, with no decisions along the way. It must work exactly as written on a clean machine; test it that way before publishing. Explanations go in other pages, linked at the end."))

def how_to():
    body = (
        h2("Goal") + p(ph("The task, in one sentence, and when you would need to do it."))
        + h2("Before you begin") + ul(ph("Access or role required"), ph("Tools and versions"), ph("Related runbook, if this touches production"))
        + h2("Steps")
        + h3("1. " + ph("First action")) + code("example do-thing --flag value")
        + h3("2. " + ph("Second action")) + p(ph("Describe UI steps as: open X, select Y, click Z."))
        + h3("3. " + ph("Third action")) + p(ph("Step."))
        + h2("Verify") + p(ph("What proves the task is done.")) + code("example status")
        + h2("Variations") + expand("[Doing this for a different environment or case]", p(ph("What changes in the steps above.")))
        + h2("Troubleshooting") + table(["Problem", "Cause", "Fix"], [[ph("Error text"), ph("Why it happens"), ph("What to do")]])
        + h2("Related") + ul(link("Getting Started"), link("Configuration Reference"), link("Runbook"))
    )
    props = std_props() + [("Audience", ph("Who this is for")), ("Applies to", ph("Product and version"))]
    return ("How-to Guide", ["how-to"], page(
        "How-to Guide", ph("One sentence: the task this page shows how to do."),
        [status("DRAFT")], props, body,
        "A how-to is a recipe for someone who already knows the basics. Title it with the task: <strong>Rotate the database password</strong>. Keep background out; link to it. Steps are numbered, verifiable, and short."))

def onboarding_checklist():
    body = (
        h2("Welcome") + p(ph("Two sentences on what the team does and how this checklist works. Your buddy and manager will go through it with you."))
        + h2("Day 1") + tasks([
            ph("Laptop received and logged in"), ph("Email, chat, and calendar working"),
            ph("Meet your onboarding buddy"), ph("Read the team charter"),
            ph("Join the team channels")])
        + h2("Week 1") + tasks([
            ph("Accounts and access from the table below requested"), ph("Development environment set up (link Getting Started)"),
            ph("Shadow one on-call shift or support rotation"), ph("First small change merged"),
            ph("Meet each person in the key people table")], start=6)
        + h2("Month 1") + tasks([
            ph("Own one ticket end to end"), ph("Read the service overviews for the systems you will support"),
            ph("Attend a change advisory meeting"), ph("30-day check-in with your manager")], start=11)
        + h2("Accounts and access") + table(["System", "Why you need it", "How to request", "Status"], [
            [ph("VPN"), ph("Reach internal systems"), ph("ServiceNow catalog item"), status("REQUESTED", "Yellow")],
            [ph("Source control"), ph("Code and infrastructure"), ph("Request group membership"), status("PENDING", "Grey")],
            [ph("Ticketing"), ph("Work intake"), ph("Automatic with AD group"), status("DONE", "Green")],
            [ph("Monitoring"), ph("Dashboards and alerts"), ph("Ask your buddy"), status("PENDING", "Grey")]])
        + h2("Tools") + table(["Tool", "Used for", "Install"], [[ph("Tool"), ph("Purpose"), ph("Link or command")]])
        + h2("Key people") + table(["Who", "Role", "Go to them for"], [
            [ph("Name"), ph("Manager"), ph("Priorities, time off, growth")],
            [ph("Name"), ph("Onboarding buddy"), ph("Anything, especially the questions you think are too small")],
            [ph("Name"), ph("Service owner"), ph("How the main system works")]])
        + h2("Reading list") + ol(link("Service Overview", "Service overviews for the systems you will support"), link("Runbook", "Runbooks you will be expected to run"), link("Standard Operating Procedure", "SOPs that apply to the team"), link("Architecture Overview", "Architecture overview"))
        + h2("Recurring meetings") + table(["Meeting", "When", "Purpose"], [[ph("Team standup"), ph("Daily 9:30 ET"), ph("Blockers and plans")]])
    )
    cards = [
        card("Buddy", PURPLE, p(ph("Name")) + p(ph("Chat handle"))),
        card("Manager", PURPLE, p(ph("Name")) + p(ph("First 1:1 date"))),
        card("First milestone", PURPLE, p(ph("First change merged by end of week 1"))),
    ]
    props = std_props() + [("New team member", ph("Name")), ("Start date", date("2026-11-03")), ("Buddy", ph("Name")), ("Manager", ph("Name"))]
    return ("Onboarding Checklist", ["onboarding"], page(
        "Onboarding Checklist", ph("One sentence: who is joining and which team."),
        [status("DRAFT"), status("WEEK 1", "Blue")], props, body,
        "Copy this page for each new team member and title it with their name. They own the checklist; the buddy reviews it weekly. Prune anything that is not actually needed in the first month.", cards))

TEMPLATES = [service_overview, architecture_overview, adr, design_doc, runbook, sop,
             troubleshooting_guide, postmortem, api_reference, configuration_reference,
             release_notes, getting_started, how_to, onboarding_checklist]

def home(entries):
    """The space home page. `entries` is a list of (title, labels)."""
    groups = [
        ("Design and decide", TEAL, ["Service Overview", "Architecture Overview", "ADR-000: Architecture Decision Record", "Design Document"]),
        ("Operate", BLUE, ["Runbook", "Standard Operating Procedure", "Troubleshooting Guide", "Incident Postmortem"]),
        ("Reference and learn", GREEN, ["API Reference", "Configuration Reference", "Release Notes", "Getting Started", "How-to Guide", "Onboarding Checklist"]),
    ]
    cards = [card(name, colour, ul(*[link(t) for t in titles])) for name, colour, titles in groups]
    band = panel(
        p("<strong>Technical documentation templates for the IT organization.</strong>")
        + p("Pick a template below, create a child page from it, and fill in the bracketed placeholders. Every template shares the same layout: a summary band, a sidebar with page properties, and a collapsed note explaining how to use it."))
    how = (
        h2("How to choose") + table(["You need to…", "Use"], [
            ["Explain what a service is and who owns it", link("Service Overview")],
            ["Describe how a system is built", link("Architecture Overview")],
            ["Record a decision and why", link("ADR-000: Architecture Decision Record")],
            ["Propose a change before building it", link("Design Document")],
            ["Tell someone how to handle an alert or routine task", link("Runbook")],
            ["Define a controlled process with approvals and audit trail", link("Standard Operating Procedure")],
            ["Help people diagnose a problem by symptom", link("Troubleshooting Guide")],
            ["Write up an incident after it is resolved", link("Incident Postmortem")],
            ["Document an API, its auth, and its errors", link("API Reference")],
            ["List every setting a component accepts", link("Configuration Reference")],
            ["Announce a version", link("Release Notes")],
            ["Walk a newcomer to a first working result", link("Getting Started")],
            ["Give a recipe for one task", link("How-to Guide")],
            ["Bring a new team member up to speed", link("Onboarding Checklist")]])
        + h2("Conventions") + ul(
            "Every page starts with a one-sentence summary in the header band. It is an excerpt, so other pages can pull it in.",
            "Page properties hold Owner, Status, and Last reviewed. The report below reads them, so keep the labels as they are.",
            "Status lozenges: " + status("DRAFT") + " " + status("IN REVIEW", "Yellow") + " " + status("APPROVED", "Green") + " " + status("DEPRECATED", "Red"),
            "Bracketed italic text is a placeholder. A page is not done until none are left.")
        + h2("All templates") + report('label = "doc-template" and space = currentSpace()', "Document type,Owner,Status,Last reviewed", "Template")
    )
    return "<ac:layout>" + section("single", band) + section("three_equal", *cards) + section("single", how) + "</ac:layout>"

# ----------------------------------------------------------------- output

def check(xml):
    """Fail on malformed XML before anything reaches Confluence."""
    wrapped = f'<r xmlns:ac="urn:ac" xmlns:ri="urn:ri">{xml}</r>'
    root = ET.fromstring(wrapped)
    for param in root.iter("{urn:ac}parameter"):
        for child in param:
            if child.tag not in ("{urn:ac}link", "{urn:ri}space", "{urn:ri}user", "{urn:ri}attachment", "{urn:ri}url"):
                raise ValueError(f"macro parameter {param.get('{urn:ac}name')!r} contains <{child.tag}>; parameters are plain text")

def pretty(xml):
    """Add newlines between block-level elements for readability. Safe to publish as is."""
    for tag in ("ac:layout-section", "ac:layout-cell", "ac:structured-macro", "ac:rich-text-body", "table", "tbody", "tr", "h2", "h3", "p", "ul", "ol", "ac:task-list", "ac:task"):
        xml = xml.replace(f"<{tag}>", f"\n<{tag}>").replace(f"<{tag} ", f"\n<{tag} ").replace(f"</{tag}>", f"</{tag}>\n")
    return "\n".join(l for l in xml.split("\n") if l.strip()) + "\n"

def build():
    pages = []
    for fn in TEMPLATES:
        title, labels, xml = fn()
        check(xml)
        pages.append((title, ["doc-template"] + labels, xml))
    hx = home([(t, l) for t, l, _ in pages])
    check(hx)
    return pages, hx

def slug(title):
    return "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-").replace("--", "-")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages"))
    a = ap.parse_args()
    pages, hx = build()
    os.makedirs(a.out, exist_ok=True)
    manifest = []
    for i, (title, labels, xml) in enumerate(pages, 1):
        name = f"{i:02d}-{slug(title)}.xml"
        open(os.path.join(a.out, name), "w").write(pretty(xml))
        manifest.append({"file": name, "title": title, "labels": labels})
    open(os.path.join(a.out, "00-home.xml"), "w").write(pretty(hx))
    import json
    json.dump({"home": "00-home.xml", "pages": manifest}, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print(f"wrote {len(pages)} templates + home to {a.out}")
