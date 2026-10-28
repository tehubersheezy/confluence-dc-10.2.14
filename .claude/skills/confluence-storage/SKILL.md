---
name: confluence-storage
description: Use when writing Confluence Data Center page bodies in storage format (XHTML) for the REST API — POST/PUT /rest/api/content with body.storage — including macros (info/note/panel/expand/code/status/toc/children/excerpt/include/page properties/jira/etc.), page links, attachments, images, user mentions, task lists, and page layouts. Also use when converting markdown or plain text into Confluence storage format.
---

# Confluence DC storage format

Page bodies sent to `POST /rest/api/content` or `PUT /rest/api/content/{id}` go in `body.storage` with `"representation": "storage"`. The value is XHTML plus `ac:` (Atlassian Confluence) and `ri:` (resource identifier) elements. Escape the XML as a JSON string.

```json
{
  "type": "page",
  "title": "Release notes",
  "space": {"key": "DOC"},
  "ancestors": [{"id": "123456"}],
  "body": {"storage": {"value": "<p>Hello</p>", "representation": "storage"}}
}
```

`PUT` requires `"version": {"number": <current + 1>}`.

Authentication: Confluence DC 10 disables Basic auth by default. Send a personal access token as `Authorization: Bearer <PAT>`.

To preview without saving, use `POST /rest/api/contentbody/convert/view`. It renders macros without page or space context, so `children`, `include`, `excerpt-include`, `pagetree`, `detailssummary`, and attachment-based macros show errors there even when the XML is correct. To test those, save a real page and read `?expand=body.view`. Macros that render in the browser can't be checked this way at all (see [When unsure](#when-unsure)).

Tested against Confluence DC 10.2.14 on 2026-10-27.

## Rules

- The body must be well-formed XHTML. Close every tag (`<br/>`, `<hr/>`), escape `&` as `&amp;`, and use no HTML entities except `&amp; &lt; &gt; &quot;` (write other characters literally as UTF-8).
- Plain XHTML is fine for `p`, `h1`–`h6`, `ul/ol/li`, `table/tbody/tr/th/td`, `strong/em/u/s/code/sub/sup`, `blockquote`, `pre`, `a href`, `hr`. Confluence removes `script`, `iframe`, and `style`. `style="text-align: center;"` on a `p` was kept in testing. Don't count on other inline styles.
- Every macro uses the `ac:structured-macro` form. Leave out `ac:macro-id`; Confluence generates it. Leave out `ac:schema-version` except for CQL-based `contentbylabel`, which needs `ac:schema-version="3"` (see reference.md). Without a schema version, Confluence assumes version 1 and migrates legacy parameters itself.
- How to write a parameter depends on its type. See [Parameter types](#parameter-types). If a parameter needs `ri:space`, `ri:user`, or a page link and you send plain text, the save fails with HTTP 500 `ClassCastException … String cannot be cast to … ResourceIdentifier` (or `… Link`).
- Body types:
  - rich: `<ac:rich-text-body>`…XHTML…`</ac:rich-text-body>`
  - plain: `<ac:plain-text-body><![CDATA[...]]></ac:plain-text-body>`. In CDATA, split any literal `]]>` as `]]]]><![CDATA[>`.
- The unnamed default parameter is `<ac:parameter ac:name="">value</ac:parameter>`. Don't use `ac:default-parameter`, which is the old `ac:macro` format.
- Boolean parameters take the strings `true` and `false`.
- Users are identified by `ri:userkey`, not username or Cloud `ri:account-id`. Look up the key with `GET /rest/api/user?username=jdoe` and read `userKey`.

## References

**Page link.** Leave out `ri:space-key` when the page is in the same space.
```xml
<ac:link><ri:page ri:space-key="DOC" ri:content-title="Install Guide"/><ac:plain-text-link-body><![CDATA[install guide]]></ac:plain-text-link-body></ac:link>
```

**Link to an anchor.** This one goes to an anchor on the same page.
```xml
<ac:link ac:anchor="setup"><ac:plain-text-link-body><![CDATA[Setup]]></ac:plain-text-link-body></ac:link>
```

**Attachment link**
```xml
<ac:link><ri:attachment ri:filename="spec.pdf"/></ac:link>
```

**User mention**
```xml
<ac:link><ri:user ri:userkey="8a7f80..."/></ac:link>
```

**Image.** It can come from an attachment or a URL. Attributes include `ac:width`, `ac:height`, `ac:align`, `ac:alt`, `ac:title`, `ac:border`, and `ac:thumbnail`.
```xml
<ac:image ac:width="400"><ri:attachment ri:filename="diagram.png"/></ac:image>
<ac:image><ri:url ri:value="https://example.com/logo.png"/></ac:image>
```

**Page reference inside a macro parameter.** Wrap the page in `ac:link`.
```xml
<ac:parameter ac:name="page"><ac:link><ri:page ri:content-title="Home"/></ac:link></ac:parameter>
```

## Parameter types

Every macro parameter has a type. Get it from the macro metadata (see [When unsure](#when-unsure)), then write the value like this:

| Type | Storage value |
|---|---|
| `confluence-content` | `<ac:link><ri:page ri:content-title="Title"/></ac:link>`. Add `ri:space-key` for another space, except in `pagetree` `root`: there, put the space in `spaces` and the title alone in `root`. `pagetree` `root` also accepts `@home`, `@self`, and `@parent` as the content title |
| `spacekey` | `<ri:space ri:space-key="KEY"/>`. For several spaces, repeat `ri:space` inside one parameter. `@all` works as a space key |
| `username` | `<ri:user ri:userkey="…"/>`, repeated for several users |
| `attachment`, `full_attachment` | `<ri:attachment ri:filename="x.pdf"/>`. The file must be on this page unless the macro has `page` |
| `url` | `<ri:url ri:value="https://…"/>` |
| everything else (`string`, `enum`, `boolean`, `int`, `label`, `group`, `cql`, `color`, `date`, `percentage`) | Plain text. Use commas when the parameter takes several values |

Exceptions to check: `gallery` `page` and `pagetreesearch` `rootPage` are `string` types (a plain page title), and `tasks-report-macro` takes `spaces` (comma-separated keys) and `pages` (comma-separated page IDs) as plain text. The `spaceAndPage` parameter its metadata lists exists only in the editor UI.

## Common macros

```xml
<!-- info | note | tip | warning: params title, icon -->
<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">Heads up</ac:parameter>
  <ac:rich-text-body><p>Maintenance window is Saturday.</p></ac:rich-text-body>
</ac:structured-macro>

<!-- panel: title, borderStyle, borderColor, borderWidth, bgColor, titleBGColor, titleColor -->
<ac:structured-macro ac:name="panel">
  <ac:parameter ac:name="title">Summary</ac:parameter>
  <ac:parameter ac:name="bgColor">#F4F5F7</ac:parameter>
  <ac:rich-text-body><p>...</p></ac:rich-text-body>
</ac:structured-macro>

<!-- expand: title -->
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">Details</ac:parameter>
  <ac:rich-text-body><p>...</p></ac:rich-text-body>
</ac:structured-macro>

<!-- code: language (lowercase id: bash, java, javascript, python, sql, xml, none…), title, linenumbers, collapse, firstline -->
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:parameter ac:name="linenumbers">true</ac:parameter>
  <ac:plain-text-body><![CDATA[print("hi")]]></ac:plain-text-body>
</ac:structured-macro>

<!-- status: colour (Grey|Red|Yellow|Green|Blue; alias color), title, subtle -->
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="colour">Green</ac:parameter>
  <ac:parameter ac:name="title">DONE</ac:parameter>
</ac:structured-macro>

<!-- toc: minLevel, maxLevel, type (list|flat), style, outline, include, exclude, printable -->
<ac:structured-macro ac:name="toc"><ac:parameter ac:name="maxLevel">3</ac:parameter></ac:structured-macro>

<!-- anchor: unnamed param = anchor name -->
<ac:structured-macro ac:name="anchor"><ac:parameter ac:name="">setup</ac:parameter></ac:structured-macro>

<!-- children: page, all, depth, first, sort (creation|title|modified), reverse, style (h1–h6), excerptType (none|simple|rich content) -->
<ac:structured-macro ac:name="children"><ac:parameter ac:name="all">true</ac:parameter></ac:structured-macro>

<!-- excerpt: hidden, atlassian-macro-output-type (BLOCK) -->
<ac:structured-macro ac:name="excerpt">
  <ac:rich-text-body><p>One-line summary reused elsewhere.</p></ac:rich-text-body>
</ac:structured-macro>

<!-- include / excerpt-include: unnamed param = page link; excerpt-include also nopanel -->
<ac:structured-macro ac:name="include">
  <ac:parameter ac:name=""><ac:link><ri:page ri:content-title="Shared Footer"/></ac:link></ac:parameter>
</ac:structured-macro>

<!-- details (Page Properties): body is a 2-column table; params id, hidden -->
<ac:structured-macro ac:name="details">
  <ac:rich-text-body>
    <table><tbody>
      <tr><th>Owner</th><td><ac:link><ri:user ri:userkey="..."/></ac:link></td></tr>
      <tr><th>Status</th><td>Draft</td></tr>
    </tbody></table>
  </ac:rich-text-body>
</ac:structured-macro>

<!-- detailssummary (Page Properties Report): label or cql; headings (columns to show), firstcolumn (title column label), sortBy, id -->
<ac:structured-macro ac:name="detailssummary">
  <ac:parameter ac:name="cql">label = &quot;project-doc&quot; and space = currentSpace()</ac:parameter>
  <ac:parameter ac:name="headings">Owner,Status</ac:parameter>
</ac:structured-macro>

<!-- jira: key (single issue) | jqlQuery + columns + maximumIssues (table) | jqlQuery + count=true ("N issues"); server, serverId, showSummary -->
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="server">Company Jira</ac:parameter>
  <ac:parameter ac:name="serverId">APPLINK-ID</ac:parameter>
  <ac:parameter ac:name="jqlQuery">project = OPS AND status != Done</ac:parameter>
  <ac:parameter ac:name="columns">key,summary,status,assignee</ac:parameter>
  <ac:parameter ac:name="maximumIssues">20</ac:parameter>
</ac:structured-macro>

<!-- jirachart: serverId, jql, chartType (pie), statType (statuses, assignees, priorities, …) -->
<ac:structured-macro ac:name="jirachart">
  <ac:parameter ac:name="serverId">APPLINK-ID</ac:parameter>
  <ac:parameter ac:name="jql">project = OPS</ac:parameter>
  <ac:parameter ac:name="chartType">pie</ac:parameter>
  <ac:parameter ac:name="statType">statuses</ac:parameter>
</ac:structured-macro>
```

The Jira macros need a working application link to Jira with OAuth impersonation enabled. Without one, `jira` shows "issue doesn't exist or you don't have permission" and `jirachart` throws a NullPointerException.

- `serverId` is the application link ID. Get it from `GET /rest/applinks/1.0/applicationlink` (`applicationLinks[].id`).
- If you leave out `server` and `serverId`, Confluence uses the primary application link. Set `serverId` when there's more than one Jira link.
- `server` is only a display name.
- Confluence caches Jira results for a few minutes, keyed by the macro's parameters. Right after you change issues in Jira, a re-saved page can still show the old status. Changing any parameter (for example the JQL order) bypasses the cache.
- In single-issue mode (`key`), the issue is rendered on the server, so `?expand=body.view` shows it. JQL tables and `count` load in the browser, so `body.view` only shows "Loading issues…". Check those in a real page view.

## Tasks and layouts

```xml
<ac:task-list>
  <ac:task>
    <ac:task-id>1</ac:task-id>
    <ac:task-status>incomplete</ac:task-status>
    <ac:task-body><ac:link><ri:user ri:userkey="..."/></ac:link> review draft by <time datetime="2026-11-15"/></ac:task-body>
  </ac:task>
</ac:task-list>

<!-- section ac:type: single | two_equal | two_left_sidebar | two_right_sidebar | three_equal | three_with_sidebars -->
<ac:layout>
  <ac:layout-section ac:type="two_equal">
    <ac:layout-cell><p>Left</p></ac:layout-cell>
    <ac:layout-cell><p>Right</p></ac:layout-cell>
  </ac:layout-section>
</ac:layout>
```

Give every task an `<ac:task-id>` that is unique on the page (1, 2, 3, …). Without one, the checkbox still displays but the task is never registered, so it has no assignee or due date and never appears in Task Report macros. Confluence doesn't add the ID for you on REST saves. In a registered task, the first user mention becomes the assignee and `<time datetime="YYYY-MM-DD"/>` becomes the due date. `ac:task-status` is `incomplete` or `complete`.

If you use layouts, all content must be inside `ac:layout`. Each section needs exactly as many cells as its type: 1, 2, or 3.

Emoticons: `<ac:emoticon ac:name="tick"/>` (also `cross`, `warning`, `information`, `smile`, `thumbs-up`, …).

## Other macros

[reference.md](reference.md) covers every other built-in macro except `html`, which is disabled by default. It gives parameters with types and allowed values, and says which macros were only partly tested.

## Examples

These files are in `examples/`. Replace the `{{USER_KEY}}`, `{{JIRA_APPLINK_ID}}`, `{{SPACE_KEY}}` and `{{PAGE_ID}}` placeholders before use. In `tested-snippets.xml`, `TEST` and `TEST2` are example space keys.

- `maintenance-hub.xml` is a complete, polished page built with layouts: a sidebar with a table of contents and page properties, status cards, a Jira table and chart, a page properties report, children, tasks, expands, and related pages. Use it as the starting point when someone wants a well-designed page.
- `runbook.xml` is a child page that the hub's page properties report and children macro read from.
- `tested-snippets.xml` contains every snippet that rendered correctly in testing, labelled by name.
- `build_showcase.py` is the source for the hub and all three runbooks. With `--out DIR`, it writes the same content as unindented XML, one file per page, named after the page title. To publish, set `CONFLUENCE_URL`, `CONFLUENCE_PAT`, `SPACE_KEY`, `USER_KEY` and `JIRA_APPLINK_ID`.

`maintenance-hub.xml` and `runbook.xml` are indented for reading. Indentation is only added between block elements, so they can be published as they are. Inside element text, `&quot;` and a literal `"` mean the same thing, so the script's output and these files are equivalent.

## When unsure

Don't guess a parameter name. Unknown parameters are saved without any error and then ignored. An unknown macro name also saves fine and renders as an "unknown macro" placeholder. The `html` macro shows the same placeholder while it's disabled, which is the default.

The instance publishes the macro definitions:

```
GET /plugins/macrobrowser/browse-macros.action?detailed=true
```

Each entry in `macros[]` has `macroName` and `formDetails.schemaVersion`. It also has `formDetails.body.bodyType` (`NONE`, `RICH_TEXT`, or `PLAIN_TEXT`) and `formDetails.parameters[]`, with `name`, `type.name`, `enumValues`, `defaultValue`, `required`, `multiple`, and `aliases`. Map `type.name` to XML using [Parameter types](#parameter-types).

Two macros aren't fully covered there. The `jira` macro's dialog writes parameters that aren't listed (`columns`, `maximumIssues`, `count`), and `tasks-report-macro` lists the UI-only `spaceAndPage`. For those, or any macro from an app, insert the macro once in the editor and copy the XML from `GET /rest/api/content/{id}?expand=body.storage`.

Some macros render in the browser, so `?expand=body.view` shows only a placeholder or JSON. That includes `jira` tables and counts, `contributors`, `contributors-summary`, and `viewxls`. Check those in a real page view.
