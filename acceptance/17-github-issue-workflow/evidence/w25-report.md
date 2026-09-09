我会按绑定实例与指定 payload 仅尝试一次；若通道离线，就保留未发布草稿并核对 decision、rule_stage 和说明，不做绕过或重试。

更新未生效，待远端可用后发布。未绕过、未重试。

- `decision`: `deny`
- `rule_stage`: `remote_upstream`
- 草稿：`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-17/gh-cache/drafts/20260909-120701-update_task-03-storm-warning.json`
- 草稿说明：远端不可用，已保存未发布草稿；不视为已发布，不静默切换本地后端。