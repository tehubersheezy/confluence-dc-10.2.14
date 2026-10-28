"""Curated Python names for the documented tiers: (METHOD, path) -> (namespace, method).

Every user-facing endpoint under /rest/api and /rest/experimental must appear here;
generate.py fails if one is missing, so new endpoints get a deliberate name.
Internal endpoints are named automatically.
"""

API = {
    # content
    ("GET", "/rest/api/content"): ("content", "list"),
    ("POST", "/rest/api/content"): ("content", "create"),
    ("GET", "/rest/api/content/scan"): ("content", "scan"),
    ("GET", "/rest/api/content/search"): ("content", "search"),
    ("GET", "/rest/api/content/{id}"): ("content", "get"),
    ("PUT", "/rest/api/content/{contentId}"): ("content", "update"),
    ("DELETE", "/rest/api/content/{id}"): ("content", "delete"),
    ("GET", "/rest/api/content/{id}/history"): ("content", "history"),
    ("GET", "/rest/api/content/{id}/history/{version}/macro/hash/{hash}"): (
        "content",
        "macro_body_by_hash",
    ),
    ("GET", "/rest/api/content/{id}/history/{version}/macro/id/{macroId}"): (
        "content",
        "macro_body_by_id",
    ),
    ("GET", "/rest/api/content/{id}/child"): ("content", "children"),
    ("GET", "/rest/api/content/{id}/child/comment"): ("content", "comments"),
    ("GET", "/rest/api/content/{id}/child/{type}"): ("content", "children_of_type"),
    ("GET", "/rest/api/content/{id}/descendant"): ("content", "descendants"),
    ("GET", "/rest/api/content/{id}/descendant/{type}"): ("content", "descendants_of_type"),
    ("DELETE", "/rest/api/content/{id}/version/{versionNumber}"): ("content", "delete_version"),
    ("POST", "/rest/api/contentbody/convert/{to}"): ("content", "convert_body"),
    ("POST", "/rest/api/content/blueprint/instance/{draftId}"): (
        "content",
        "publish_blueprint_draft",
    ),
    ("PUT", "/rest/api/content/blueprint/instance/{draftId}"): (
        "content",
        "publish_shared_blueprint_draft",
    ),
    # attachments
    ("GET", "/rest/api/content/{id}/child/attachment"): ("attachments", "list"),
    ("POST", "/rest/api/content/{id}/child/attachment"): ("attachments", "create"),
    ("PUT", "/rest/api/content/{id}/child/attachment/{attachmentId}"): ("attachments", "update"),
    ("POST", "/rest/api/content/{id}/child/attachment/{attachmentId}/data"): (
        "attachments",
        "update_data",
    ),
    ("DELETE", "/rest/api/content/{id}/child/attachment/{attachmentId}"): ("attachments", "delete"),
    ("DELETE", "/rest/api/content/{id}/child/attachment/{attachmentId}/version/{version}"): (
        "attachments",
        "delete_version",
    ),
    ("GET", "/rest/api/content/{id}/child/attachment/{attachmentId}/extractedtext"): (
        "attachments",
        "extracted_text",
        "Get the text Confluence extracted from an attachment (for search)",
    ),
    ("POST", "/rest/api/content/{id}/child/attachment/{attachmentId}/move"): (
        "attachments",
        "move",
    ),
    # labels
    ("GET", "/rest/api/content/{id}/label"): ("labels", "for_content"),
    ("POST", "/rest/api/content/{id}/label"): ("labels", "add_to_content"),
    ("DELETE", "/rest/api/content/{id}/label/{label}"): ("labels", "remove_from_content"),
    ("DELETE", "/rest/api/content/{id}/label"): ("labels", "remove_from_content_by_name"),
    ("GET", "/rest/api/label/labels"): ("labels", "list"),
    ("GET", "/rest/api/label/popular"): ("labels", "popular"),
    ("GET", "/rest/api/label/recent"): ("labels", "recent"),
    ("GET", "/rest/api/label/{labelName}/related"): ("labels", "related"),
    ("GET", "/rest/api/space/{spaceKey}/labels"): ("labels", "for_space"),
    ("GET", "/rest/api/space/{spaceKey}/labels/popular"): ("labels", "popular_in_space"),
    ("GET", "/rest/api/space/{spaceKey}/labels/recent"): ("labels", "recent_in_space"),
    ("GET", "/rest/api/space/{spaceKey}/labels/{labelName}/related"): (
        "labels",
        "related_in_space",
    ),
    # content properties
    ("GET", "/rest/api/content/{id}/property"): ("content_properties", "list"),
    ("POST", "/rest/api/content/{id}/property"): ("content_properties", "create"),
    ("GET", "/rest/api/content/{id}/property/{key}"): ("content_properties", "get"),
    ("POST", "/rest/api/content/{id}/property/{key}"): (
        "content_properties",
        "create_with_key",
        "Create a content property under the key in the path",
    ),
    ("PUT", "/rest/api/content/{id}/property/{key}"): ("content_properties", "update"),
    ("DELETE", "/rest/api/content/{id}/property/{key}"): ("content_properties", "delete"),
    # restrictions
    ("PUT", "/rest/api/content/{id}/restriction"): ("restrictions", "update"),
    ("GET", "/rest/api/content/{id}/restriction/byOperation"): ("restrictions", "by_operation"),
    ("GET", "/rest/api/content/{id}/restriction/byOperation/{operationKey}"): (
        "restrictions",
        "for_operation",
    ),
    ("GET", "/rest/api/content/{id}/restriction/relevantViewRestrictions"): (
        "restrictions",
        "relevant_view_restrictions",
    ),
    # watching
    ("GET", "/rest/api/content/{contentId}/watchers"): ("watches", "content_watchers"),
    ("GET", "/rest/api/space/{spaceKey}/watchers"): ("watches", "space_watchers"),
    ("GET", "/rest/api/user/watch/content/{contentId}"): ("watches", "is_watching_content"),
    ("POST", "/rest/api/user/watch/content/{contentId}"): ("watches", "watch_content"),
    ("DELETE", "/rest/api/user/watch/content/{contentId}"): ("watches", "unwatch_content"),
    ("GET", "/rest/api/user/watch/space/{spaceKey}"): ("watches", "is_watching_space"),
    ("POST", "/rest/api/user/watch/space/{spaceKey}"): ("watches", "watch_space"),
    ("DELETE", "/rest/api/user/watch/space/{spaceKey}"): ("watches", "unwatch_space"),
    # spaces
    ("GET", "/rest/api/space"): ("spaces", "list"),
    ("POST", "/rest/api/space"): ("spaces", "create"),
    ("POST", "/rest/api/space/_private"): ("spaces", "create_private"),
    ("POST", "/rest/api/space/personal"): ("spaces", "create_personal"),
    ("GET", "/rest/api/space/{spaceKey}"): ("spaces", "get"),
    ("PUT", "/rest/api/space/{spaceKey}"): ("spaces", "update"),
    ("DELETE", "/rest/api/space/{spaceKey}"): ("spaces", "delete"),
    ("PUT", "/rest/api/space/{spaceKey}/archive"): ("spaces", "archive"),
    ("PUT", "/rest/api/space/{spaceKey}/restore"): ("spaces", "restore"),
    ("GET", "/rest/api/space/{spaceKey}/content"): ("spaces", "contents"),
    ("GET", "/rest/api/space/{spaceKey}/content/{type}"): ("spaces", "contents_of_type"),
    ("GET", "/rest/api/space/{spaceKey}/trash"): ("spaces", "trash"),
    ("DELETE", "/rest/api/space/{spaceKey}/trash"): ("spaces", "empty_trash"),
    ("POST", "/rest/api/space/{spaceKey}/category/{labelName}"): ("spaces", "add_category"),
    ("DELETE", "/rest/api/space/{spaceKey}/category/{categoryName}"): ("spaces", "remove_category"),
    ("GET", "/rest/api/space/{spaceKey}/color-scheme"): ("spaces", "color_scheme"),
    ("PUT", "/rest/api/space/{spaceKey}/color-scheme"): ("spaces", "update_color_scheme"),
    ("PUT", "/rest/api/space/{spaceKey}/color-scheme/reset"): ("spaces", "reset_color_scheme"),
    ("GET", "/rest/api/space/{spaceKey}/color-scheme/type"): ("spaces", "color_scheme_type"),
    ("PUT", "/rest/api/space/{spaceKey}/color-scheme/type"): ("spaces", "update_color_scheme_type"),
    # space properties
    ("GET", "/rest/api/space/{spaceKey}/property"): ("space_properties", "list"),
    ("POST", "/rest/api/space/{spaceKey}/property"): ("space_properties", "create"),
    ("GET", "/rest/api/space/{spaceKey}/property/{key}"): ("space_properties", "get"),
    ("POST", "/rest/api/space/{spaceKey}/property/{key}"): ("space_properties", "create_with_key"),
    ("PUT", "/rest/api/space/{spaceKey}/property/{key}"): ("space_properties", "update"),
    ("DELETE", "/rest/api/space/{spaceKey}/property/{key}"): ("space_properties", "delete"),
    # space permissions (space admins)
    ("GET", "/rest/api/space/{spaceKey}/permissions"): ("space_permissions", "list"),
    ("POST", "/rest/api/space/{spaceKey}/permissions"): ("space_permissions", "set"),
    ("GET", "/rest/api/space/{spaceKey}/permissions/anonymous"): (
        "space_permissions",
        "for_anonymous",
    ),
    ("PUT", "/rest/api/space/{spaceKey}/permissions/anonymous/grant"): (
        "space_permissions",
        "grant_anonymous",
    ),
    ("PUT", "/rest/api/space/{spaceKey}/permissions/anonymous/revoke"): (
        "space_permissions",
        "revoke_anonymous",
    ),
    ("GET", "/rest/api/space/{spaceKey}/permissions/group/{groupName}"): (
        "space_permissions",
        "for_group",
    ),
    ("PUT", "/rest/api/space/{spaceKey}/permissions/group/{groupName}/grant"): (
        "space_permissions",
        "grant_group",
    ),
    ("PUT", "/rest/api/space/{spaceKey}/permissions/group/{groupName}/revoke"): (
        "space_permissions",
        "revoke_group",
    ),
    ("GET", "/rest/api/space/{spaceKey}/permissions/user/{userKey}"): (
        "space_permissions",
        "for_user",
    ),
    ("PUT", "/rest/api/space/{spaceKey}/permissions/user/{userKey}/grant"): (
        "space_permissions",
        "grant_user",
    ),
    ("PUT", "/rest/api/space/{spaceKey}/permissions/user/{userKey}/revoke"): (
        "space_permissions",
        "revoke_user",
    ),
    # users & groups
    ("GET", "/rest/api/user"): ("users", "get"),
    ("GET", "/rest/api/user/anonymous"): ("users", "anonymous"),
    ("GET", "/rest/api/user/current"): ("users", "current"),
    ("PUT", "/rest/api/user/current"): ("users", "update_current"),
    ("POST", "/rest/api/user/current/password"): ("users", "change_password"),
    ("GET", "/rest/api/user/list"): ("users", "list"),
    ("GET", "/rest/api/user/memberof"): ("users", "groups"),
    ("PUT", "/rest/api/user/settings"): ("users", "update_settings"),
    ("GET", "/rest/api/group"): ("groups", "list"),
    ("GET", "/rest/api/group/info"): ("groups", "info"),
    ("GET", "/rest/api/group/{groupName}"): ("groups", "get"),
    ("GET", "/rest/api/group/{groupName}/member"): ("groups", "members"),
    ("GET", "/rest/api/group/{groupName}/groupmember"): ("groups", "nested_members"),
    # search, tasks, server
    ("GET", "/rest/api/search"): ("search", "cql"),
    ("GET", "/rest/api/longtask"): ("long_tasks", "list"),
    ("GET", "/rest/api/longtask/{id}"): ("long_tasks", "get"),
    ("GET", "/rest/api/server-information"): ("server", "info"),
    ("GET", "/rest/api/accessmode"): ("server", "access_mode"),
    ("GET", "/rest/api/color-scheme"): ("server", "color_scheme"),
    # space backups (space admins)
    ("POST", "/rest/api/backup-restore/backup/space"): ("backups", "create_space_backup"),
    ("GET", "/rest/api/backup-restore/jobs"): ("backups", "jobs"),
    ("GET", "/rest/api/backup-restore/jobs/{jobId}"): ("backups", "job"),
    ("PUT", "/rest/api/backup-restore/jobs/{jobId}/cancel"): ("backups", "cancel_job"),
    ("GET", "/rest/api/backup-restore/jobs/{jobId}/download"): ("backups", "download"),
}

EXPERIMENTAL = {
    # page templates and blueprints
    ("GET", "/rest/experimental/template/page"): (
        "templates",
        "list",
        "List page templates in a space, or global templates when space_key is omitted",
    ),
    ("GET", "/rest/experimental/template/blueprint"): (
        "templates",
        "list_blueprint_templates",
        "List blueprint templates in a space, or global ones when space_key is omitted",
    ),
    ("GET", "/rest/experimental/template/{contentTemplateId}"): (
        "templates",
        "get",
        "Get a page or blueprint template by ID",
    ),
    ("POST", "/rest/experimental/template"): (
        "templates",
        "create",
        "Create a page template (space-scoped when body.space is set, otherwise global)",
    ),
    ("PUT", "/rest/experimental/template"): (
        "templates",
        "update",
        "Update a page template; body must include templateId",
    ),
    ("DELETE", "/rest/experimental/template/{contentTemplateId}"): (
        "templates",
        "delete",
        "Delete a page template",
    ),
    ("POST", "/rest/experimental/template/page/{contentTemplateId}/instance"): (
        "templates",
        "create_content",
        "Create a page or draft from a page template",
    ),
    ("POST", "/rest/experimental/cc/content/blueprint/{blueprintId}/instance"): (
        "templates",
        "create_content_from_blueprint",
        "Create a page or draft from a blueprint",
    ),
    # content versions
    ("GET", "/rest/experimental/content/{id}/version"): (
        "content_versions",
        "list",
        "List a page's historical versions",
    ),
    ("GET", "/rest/experimental/content/{id}/version/{versionNumber}"): (
        "content_versions",
        "get",
        "Get one historical version of a page",
    ),
    ("POST", "/rest/experimental/content/{id}/version"): (
        "content_versions",
        "restore",
        "Restore a historical version as the current version",
    ),
    ("DELETE", "/rest/experimental/content/{id}/version/{versionId}"): (
        "content_versions",
        "delete",
        "Delete a historical version",
    ),
    # restrictions
    ("GET", "/rest/experimental/content/{id}/restriction"): (
        "restrictions",
        "get",
        "Get view and edit restrictions on content",
    ),
    ("POST", "/rest/experimental/content/{id}/restriction"): (
        "restrictions",
        "add",
        "Add restrictions to content",
    ),
    ("PUT", "/rest/experimental/content/{id}/restriction"): (
        "restrictions",
        "update",
        "Replace restrictions on content",
    ),
    ("DELETE", "/rest/experimental/content/{id}/restriction"): (
        "restrictions",
        "delete_all",
        "Remove all restrictions from content",
    ),
    (
        "GET",
        "/rest/experimental/content/{id}/restriction/byOperation/{operationKey}/group/{groupName}",
    ): ("restrictions", "group_status", "Check whether a group is in a content restriction"),
    (
        "PUT",
        "/rest/experimental/content/{id}/restriction/byOperation/{operationKey}/group/{groupName}",
    ): ("restrictions", "add_group", "Add a group to a content restriction"),
    (
        "DELETE",
        "/rest/experimental/content/{id}/restriction/byOperation/{operationKey}/group/{groupName}",
    ): ("restrictions", "remove_group", "Remove a group from a content restriction"),
    ("GET", "/rest/experimental/content/{id}/restriction/byOperation/{operationKey}/user"): (
        "restrictions",
        "user_status",
        "Check whether a user is in a content restriction",
    ),
    ("PUT", "/rest/experimental/content/{id}/restriction/byOperation/{operationKey}/user"): (
        "restrictions",
        "add_user",
        "Add a user to a content restriction",
    ),
    ("DELETE", "/rest/experimental/content/{id}/restriction/byOperation/{operationKey}/user"): (
        "restrictions",
        "remove_user",
        "Remove a user from a content restriction",
    ),
    # users, groups, search
    ("GET", "/rest/experimental/user"): ("users", "get", "Get a user by username or key"),
    ("GET", "/rest/experimental/user/anonymous"): ("users", "anonymous", "Get the anonymous user"),
    ("GET", "/rest/experimental/user/current"): ("users", "current", "Get the calling user"),
    ("GET", "/rest/experimental/user/memberof"): (
        "users",
        "groups",
        "List the groups a user belongs to",
    ),
    ("GET", "/rest/experimental/group"): ("groups", "list", "List groups"),
    ("GET", "/rest/experimental/group/{groupName}"): ("groups", "get", "Get a group"),
    ("GET", "/rest/experimental/group/{groupName}/member"): (
        "groups",
        "members",
        "List a group's members",
    ),
    ("GET", "/rest/experimental/search"): ("search", "cql", "Search with CQL"),
    # relations (e.g. favourites: user -favourite-> content)
    (
        "GET",
        "/rest/experimental/relation/{sourceType}/{sourceKey}/{relationName}/to{targetType}/{targetKey}",
    ): ("relations", "exists", "Check whether a relation exists, e.g. user -favourite-> content"),
    (
        "PUT",
        "/rest/experimental/relation/{sourceType}/{sourceKey}/{relationName}/to{targetType}/{targetKey}",
    ): ("relations", "create", "Create a relation, e.g. favourite a page"),
    (
        "DELETE",
        "/rest/experimental/relation/{sourceType}/{sourceKey}/{relationName}/to{targetType}/{targetKey}",
    ): ("relations", "delete", "Delete a relation, e.g. unfavourite a page"),
    # web fragments (UI panels, sections, items)
    ("GET", "/rest/experimental/webfragment/panels"): (
        "web_fragments",
        "panels",
        "List web panels",
    ),
    ("GET", "/rest/experimental/webfragment/panels/{location}"): (
        "web_fragments",
        "panels_at",
        "List web panels at a UI location",
    ),
    ("GET", "/rest/experimental/webfragment/section"): (
        "web_fragments",
        "sections",
        "List web sections",
    ),
    ("GET", "/rest/experimental/webfragment/section/{location}"): (
        "web_fragments",
        "sections_at",
        "List web sections at a UI location",
    ),
    ("GET", "/rest/experimental/webfragment/section/{location}/{section}/items"): (
        "web_fragments",
        "items",
        "List web items in a section",
    ),
}

# Extra docstring text for endpoints whose request shape isn't obvious.
# Each example was verified against Confluence DC 10.2.14.
NOTES = {
    ("POST", "/rest/experimental/template"): """Example body::

    {"name": "Runbook", "templateType": "page", "description": "...",
     "body": {"storage": {"value": "<p>...</p>", "representation": "storage"}},
     "labels": [{"prefix": "global", "name": "runbook"}],
     "space": {"key": "DOCS"}}

Omit ``space`` for a global template (needs Confluence admin). Space templates
need space admin.""",
    ("PUT", "/rest/experimental/template"): """Send the full template, including ``templateId``,
``templateType`` and ``space``; omitted fields are cleared.""",
    (
        "POST",
        "/rest/experimental/template/page/{contentTemplateId}/instance",
    ): """Example body (the ID must match ``content_template_id``)::

    {"content": {"type": "page", "title": "New page", "space": {"key": "DOCS"},
                 "ancestors": [{"id": "123"}]},
     "contentBlueprintSpec": {"contentTemplateId": "917508", "context": {}}}

Add ``"status": "draft"`` to ``content`` to create a draft instead.""",
    ("POST", "/rest/api/content/{id}/child/attachment"): """Example::

    c.attachments.create(page_id, {"file": ("diagram.png", fh, "image/png")},
                         data={"comment": "v1", "minorEdit": "true"})""",
}
