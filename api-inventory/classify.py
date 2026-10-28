"""Turn the raw scan (+ optional live probe) into inventory.json for codegen.

  python3 api-inventory/classify.py
Adds per endpoint:
  audience: "user" or "admin"   (admin endpoints are left out of the library)
  tier:     "api" | "experimental" | "internal"
  probe:    {"admin": status, "user": status} when the endpoint was probed live
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ACCESS = ("AdminOnly", "SystemAdminOnly", "LicensedOnly", "AnonymousSiteAccess", "UnrestrictedAccess", "UnlicensedSiteAccess")
ADMIN_FILTERS = ("AdminOnlyResourceFilter", "AdminApplicationLinksFilterBinding", "UserIsAdmin", "UserIsSystemAdmin")
# Not features: test-data generators and alias mounts of other modules.
EXCLUDE = (re.compile(r"^/rest/token-auth/"), re.compile(r"/detailssummarytest/"))
# Admin checks done in code, found by reading the resource or probing a sibling endpoint.
ADMIN_CLASSES = {
    "com.atlassian.confluence.plugins.restapi.resources.GlobalWebhooksResource",
    "com.atlassian.confluence.plugins.restapi.experimental.resources.SynchronyDataEvictionResource",
}


def short(t): return t.split(".")[-1]


def access_of(e):
    m = [short(t) for t in e["method_annotations"]]
    c = [short(a["type"]) for a in e["annotations"]]
    return next((a for a in m if a in ACCESS), None) or next((a for a in c if a in ACCESS), None) or "LicensedOnly"


def annotated_admin(e, access):
    anns = e["annotations"]
    names = [short(a["type"]) for a in anns]
    sudo = "WebSudoRequired" in names and "WebSudoNotRequired" not in [short(t) for t in e["method_annotations"]]
    filt = any(f in json.dumps(a["values"]) or short(a["type"]) == f for a in anns for f in ADMIN_FILTERS)
    scopes = [s for a in anns if short(a["type"]) == "ScopesAllowed" for s in a["values"].get("requiredScope", [])]
    admin_scope = bool(scopes) and all(s in ("ADMIN", "SYSTEM_ADMIN") for s in scopes)
    admin_path = re.search(r"/admin(/|$)", e["path"]) is not None
    return access in ("AdminOnly", "SystemAdminOnly") or sudo or filt or admin_scope or admin_path


def tier_of(e):
    base = e["module_base"]
    if base == "/rest/api": return "api"
    if base.startswith("/rest/experimental"): return "experimental"
    return "internal"


def main():
    scan = json.load(open(os.path.join(HERE, "endpoints.json")))
    probe_path = os.path.join(HERE, "probe.json")
    probe = json.load(open(probe_path)) if os.path.exists(probe_path) else {}
    out = {}
    for e in scan["endpoints"]:
        if any(rx.search(e["path"]) for rx in EXCLUDE): continue
        key = (e["method"], e["path"])
        if key in out: continue
        access = access_of(e)
        admin = annotated_admin(e, access)
        p = probe.get(e["path"]) if e["method"] == "GET" else None
        if p:
            ok = lambda s: isinstance(s, int) and 200 <= s < 300
            if ok(p["user"]): admin = False
            elif ok(p["admin"]) and p["user"] in (401, 403): admin = True
        out[key] = {**e, "access": access, "audience": "admin" if admin else "user", "tier": tier_of(e),
                    **({"probe": p} if p else {})}
    # A class whose probed GETs are all admin-only is treated as admin-only throughout.
    by_class = {}
    for e in out.values(): by_class.setdefault(e["class"], []).append(e)
    for cls, es in by_class.items():
        probed = [e for e in es if "probe" in e]
        ok = lambda s: isinstance(s, int) and 200 <= s < 300
        admin_probe = any(ok(e["probe"]["admin"]) and e["probe"]["user"] in (401, 403) for e in probed)
        user_probe = any(ok(e["probe"]["user"]) for e in probed)
        if cls in ADMIN_CLASSES or (admin_probe and not user_probe):
            for e in es: e["audience"] = "admin"
    endpoints = sorted(out.values(), key=lambda e: (e["path"], e["method"]))
    json.dump({"endpoints": endpoints, "models": scan["models"]}, open(os.path.join(HERE, "inventory.json"), "w"), indent=1)
    users = [e for e in endpoints if e["audience"] == "user"]
    from collections import Counter
    print(len(endpoints), "endpoints;", len(users), "user-facing;", Counter(e["tier"] for e in users))


main()
