"""Call every parameter-free GET endpoint as the admin and the regular user.

  set -a; source .env; set +a
  python3 api-inventory/probe.py api-inventory/endpoints.json api-inventory/probe.json
"""
import concurrent.futures as cf, json, os, sys, urllib.error, urllib.request

BASE = os.environ.get("CONFLUENCE_URL", "http://localhost:8095")
TOKENS = {"admin": os.environ["CONFLUENCE_PAT"], "user": os.environ["CONFLUENCE_USER_PAT"]}


def call(path, who):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOKENS[who], "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp: return resp.status
    except urllib.error.HTTPError as e: return e.code
    except Exception as e: return type(e).__name__


def main(src, dst):
    endpoints = json.load(open(src))["endpoints"]
    paths = sorted({e["path"] for e in endpoints if e["method"] == "GET" and "{" not in e["path"]})
    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(zip(paths, ex.map(lambda p: {"admin": call(p, "admin"), "user": call(p, "user")}, paths)))
    json.dump(res, open(dst, "w"), indent=1, sort_keys=True)
    print(len(res), "paths probed")


main(*sys.argv[1:3])
