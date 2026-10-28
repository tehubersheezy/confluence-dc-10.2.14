# IT documentation templates

Fourteen technical documentation templates for an IT organization, written in Confluence storage format, plus a space home page that indexes them.

| Family | Templates |
|---|---|
| Design and decide | Service Overview, Architecture Overview, Architecture Decision Record, Design Document |
| Operate | Runbook, Standard Operating Procedure, Troubleshooting Guide, Incident Postmortem |
| Reference and learn | API Reference, Configuration Reference, Release Notes, Getting Started, How-to Guide, Onboarding Checklist |

Every page shares one design: a grey header band with a one-sentence excerpt and status lozenges, an optional row of three accent-coloured cards for the facts people look for first, then a two-column body with the content on the left and a sidebar holding the table of contents, the page properties, and a collapsed "About this template" note. Page properties always include Document type, Owner, Status, and Last reviewed, so the home page's Page Properties Report can list them all.

## Files

- `build.py` — the source. Each template is a function; shared helpers produce the layout, cards, tables, callouts, and task lists. Run it to regenerate `pages/`. It fails if any page is malformed XML or puts markup inside a macro parameter.
- `pages/*.xml` — generated storage-format bodies, one per page, numbered in display order. `00-home.xml` is the space home. `manifest.json` lists titles and labels.
- `publish.py` — upserts the pages by title under a space home page, applies labels, and reports rendering errors from `body.view`. With `--space-templates` it also registers each page as a space page template, so they appear under Create > Templates.

## Publish

```sh
set -a; source .env; set +a          # CONFLUENCE_PAT; optional CONFLUENCE_URL, SPACE_KEY, USER_KEY, JIRA_APPLINK_ID
python3 templates/build.py
python3 templates/publish.py --space-templates
python3 templates/publish.py --check  # re-scan published pages for macro errors
```

The space (default `ITDOC`) must already exist. `{{USER_KEY}}` becomes the PAT's user and `{{JIRA_APPLINK_ID}}` becomes the primary Jira application link; without a link, the Jira macros fall back to Confluence's default.
