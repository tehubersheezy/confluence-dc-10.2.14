# confluence-dc-10.2.14

A local Confluence Data Center 10.2.14 running in Docker, with PostgreSQL 16, at http://localhost:8095. It's used to test Confluence storage-format XML. The skill itself is in `~/Projects/confluence-storage`.

## Run

```sh
cp .env.example .env   # fill in the values; the license is the 3-hour DC timebomb key
docker compose up -d
```

The license key in `ATL_LICENSE_KEY` skips the license step of the setup wizard. The 3-hour clock restarts each time the app starts, so `docker compose restart confluence` gives you another 3 hours.

## Jira link

The application link goes to the local Jira in `~/Projects/jira-dc-10.3.26`, with OAuth impersonation enabled. Confluence reaches Jira over Jira's Docker network. That connection isn't in the compose file, so reconnect it after the container is recreated:

```sh
docker network connect jira-dc_default confluence
```

## storage-tests

These are the scripts used to verify the skill. Each snippet is saved as its own page under a parent page, and the script prints any rendering errors:

```sh
set -a; source .env; set +a
python3 storage-tests/perpage.py storage-tests/snips.json <parentPageId> <unusedPageId>
```

The files are:
- `snips*.json`: the test cases. `USERKEY` is replaced at runtime.
- `run.py`: the first-round runner. It uses the convert endpoint and then saves the pages.
- `macros.txt`: a dump of this instance's macro metadata.
- `diagram.png`, `spec.pdf`, `book.xlsx`, `deck.pptx`: attached to the `att-*` test pages.

The user key and application link ID are hard-coded for this instance.
