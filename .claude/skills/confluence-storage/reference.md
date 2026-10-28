# Macro reference (Confluence DC 10.2.14)

Parameter names, types and allowed values come from the instance's own macro metadata (`/plugins/macrobrowser/browse-macros.action?detailed=true`). The macros are live-tested unless a row's notes say otherwise. [space] and [page] brackets follow the metadata types. Each value is written according to [Parameter types](SKILL.md#parameter-types). The type is shown in brackets only when it isn't plain text: **[page]**, **[space]**, **[user]**, **[att]**, **[url]**. `+` means several values are allowed, `=` gives the default, and `!` means required.

Body: **rich** = `ac:rich-text-body`, **plain** = `ac:plain-text-body` with CDATA, **—** = no body.

## Navigation and listing

| ac:name | Body | Parameters | Notes |
|---|---|---|---|
| `pagetree` | — | `root` [page] (or `@home` / `@self` / `@parent` as the title), `spaces` [space], `sort` = bitwise\|creation\|modified\|natural\|position (=position), `excerpt`, `reverse`, `searchBox`, `expandCollapseAll`, `startDepth`=1 | For another space, set `spaces` and give `root` the title only. Don't use `ri:space-key` in `root` |
| `pagetreesearch` | — | `rootPage` (plain title) | |
| `contentbylabel` | — | `ac:schema-version="3"` with `cql`!, `max`=15, `sort` = title\|creation\|modified, `reverse`, `title`, `showLabels`, `showSpace`, `excludeCurrent`, `excerptType` = none\|simple\|rich content | Without `ac:schema-version="3"`, `cql` fails. Legacy `labels`/`spaces` parameters without a schema version are migrated on save |
| `content-report-table` | — | `labels`!, `spaces` [space]+, `maxResults`=20, `showCommentsCount`, `showLikesCount` | |
| `recently-updated` | — | `spaces` [space]+ (`@all` works), `author` [user]+, `labels`, `types` = page,blogpost,comment,attachment, `max`=15, `theme` = concise\|social\|sidebar, `showProfilePic`, `hideHeading`, `width` | Leave out `spaces` for the current space |
| `recently-updated-dashboard` | — | `spaces` [space]+, `types`+, `labels`+, `users` [user]+, `width`, `showProfilePic` | |
| `blog-posts` | — | `content` = titles\|excerpts\|entire (=entire; the metadata marks it required, but leaving it out rendered without error), `spaces` [space], `author` [user]+, `labels`, `time` (e.g. `7d`), `max`=100, `sort` = title\|creation\|modified, `reverse` | |
| `content-by-user` | — | `""` [user]! | |
| `index` | — | none | Lists every page in the space |
| `navmap` | — | `""` = label!, `title`, `wrapAfter`=5, `cellWidth`, `cellHeight`, `theme` | |
| `spaces` | — | `""` = all\|category\|favourite\|new, `width`, `includeArchivedSpaces` | |
| `livesearch` | — | `spaceKey` [space], `labels`, `size` = medium\|large, `placeholder`, `type` = all\|page\|blogpost\|comment\|spacedesc, `additional` = none\|space name\|page excerpt | |
| `favpages` | — | none | |
| `change-history` | — | `limit` | |
| `global-reports` | — | `width` | |
| `create-space-button` | — | `size` = small\|large | |

## Labels

| ac:name | Body | Parameters |
|---|---|---|
| `listlabels` | — | `spaceKey` [space], `count`=100, `excludedLabels`+ |
| `popular-labels` | — | `spaceKey` [space], `count`=100, `style` = list\|heatmap |
| `recently-used-labels` | — | `scope` = global\|space\|personal, `style` = list\|table, `count`=10, `title` |
| `related-labels` | — | `labels` |

## Files and media

| ac:name | Body | Parameters | Notes |
|---|---|---|---|
| `attachments` | — | `patterns` (regex), `labels`, `sortBy` = date\|createddate\|size\|name, `sortOrder`, `old`, `preview`, `upload`, `page` [page] | |
| `space-attachments` | — | `space` [space], `showFilter` | |
| `gallery` | — | `page` (**plain title**, not a link), `title`, `columns`=4, `include`, `exclude`, `includeLabel`, `excludeLabel`, `sort` = name\|comment\|date\|size, `reverse` | |
| `viewpdf`, `viewdoc` | — | `name` [att]!, `page` [page] | Only `viewpdf` was tested |
| `viewxls` | — | `name` [att]!, `page` [page], `sheet`, `grid`, `row`, `col` | Renders in the browser |
| `viewppt` | — | `name` [att]!, `page` [page], `slide`, `width`, `height` | |
| `view-file` | — | `name` [att]!, `page` [page], `space` [space], `date` | Generic file preview |
| `multimedia` | — | `name` [att]!, `page` [page], `width`, `height`, `autostart` | Video and audio only. Only tested with an image, which gave an "Unable to display content of type" error |
| `widget` | — | `url` [url]!, `width`, `height` | |
| `rss` | — | `url` [url]!, `max`=15, `showTitlesOnly`, `titleBar` | Only tested as far as the allowlist error. The feed host must be on the admin allowlist. Otherwise it shows "not from an allowed source" |

## People

| ac:name | Body | Parameters | Notes |
|---|---|---|---|
| `profile` | — | `user` [user]! | |
| `profile-picture` | — | `User` [user]! (capital U) | |
| `userlister` | — | `groups`+!, `online` = true\|false | |
| `network` | — | `""` = following\|followers!, `username` [user], `theme` = full\|tiny, `max` | |
| `contributors` | — | `include` = authors,comments,labels,watches, `mode` = inline\|list, `order` = count\|name\|update, `limit`, `page` [page], `spaces` [space]+, `labels`+, `scope` = children\|descendants, `contentType` = pages\|blogposts, `publishDate`, `showCount`, `showLastTime`, `showPages`, `showAnonymous`, `reverse`, `noneFoundMessage` | Renders in the browser |
| `contributors-summary` | — | `groupby` = contributors\|pages, `columns` = edits,edited,comments,commented,labels,labeled,labellist,watches,watching,lastupdate, `order`, `limit`, `page` [page], `spaces` [space]+, `labels`+, `scope`, `contentType`, `publishDate`, `showAnonymous`, `showZeroCounts`, `reverse` | Renders in the browser |

## Tasks

| ac:name | Body | Parameters | Notes |
|---|---|---|---|
| `tasks-report-macro` | — | `spaces` (comma-separated keys, plain text), `pages` (comma-separated page IDs), `assignees` [user]+, `creators` [user]+, `labels`+, `status` = incomplete\|complete, `createddateFrom`, `columns` = description,duedate,assignee,location, `sortBy` = due date\|assignee\|page title, `reverseSort`, `pageSize` = 10\|20\|40 | Only shows tasks that have `<ac:task-id>`. Don't use `spaceAndPage` (editor UI only) or the singular `assignee` (ignored) |

## Layout and content

| ac:name | Body | Parameters |
|---|---|---|
| `toc-zone` | rich | `location` = both\|top\|bottom, plus every `toc` parameter |
| `toc` | — | `type` = list\|flat, `separator` = brackets\|braces\|parens\|pipe\|text, `outline`, `style` (CSS list style), `indent`, `minLevel`, `maxLevel`, `include`, `exclude` (regex), `printable`, `class`, `absoluteUrl` |
| `section` | rich | `border`. The body holds `column` macros |
| `column` | rich | `width` (px or %). Prefer `ac:layout` |
| `chart` | rich | `type` = pie\|bar\|line\|area\|xyArea\|xyBar\|xyLine\|xyStep\|xyStepArea\|scatter\|timeSeries\|gantt, `title`, `subTitle`, `xLabel`, `yLabel`, `width`, `height`, `legend`, `orientation`, `dataOrientation`, `3D`, `stacked`, `colors`+, `bgColor`, plus about 25 more axis and format options in the metadata. The body is the data table |
| `create-from-template` | — | `blueprintModuleCompleteKey` or `templateId`, `buttonLabel`, `title`, `spaceKey` [space]. Get blueprint keys from `GET /rest/create-dialog/1.0/blueprints/web-items?spaceKey=KEY` |
| `loremipsum` | — | `""` = paragraph count |
| `noformat` | plain | `nopanel` |

## Untested (parameters from metadata only)

| ac:name | Body | Parameters |
|---|---|---|
| `calendar` (Team Calendars) | — | `id`! (alias `subCalendars`), `defaultView` = month\|week\|list\|timeline, `width`, `height`, `showLegend` = none\|bottom\|right, `hideWeekends` |
| `portfolio-for-jira-plan` (Advanced Roadmaps) | — | `url`!, `height`! |
