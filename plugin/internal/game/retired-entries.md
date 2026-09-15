# 旧入口与 gate 去向

本说明是已退役公开入口和 mgs-gate 的去向索引。列出的旧名称只用于解释迁移，**不是可执行别名**、提示占位入口或可选模式。

最终公开集合只有 Matt 正式 25 项加 Game-Producer、Game-Init、Game-Design。

## 旧入口去向

- game-status -> game-producer
- game-plan -> to-tickets
- game-spec -> to-spec
- game-implement -> implement
- game-code -> on-demand-reference
- game-art -> task
- game-audio -> task
- game-build -> task
- game-review -> task
- game-playtest -> task
- game-prototype -> task

`game-status` 的只读查询并入 Game-Producer。`game-plan` / `game-spec` / `game-implement` 的通用职责分别交给 `to-tickets` / `to-spec` / `implement`。`game-code` 的适用内容成为按需参考，不再作为独立入口。`game-art` / `game-audio` / `game-build` / `game-review` / `game-playtest` / `game-prototype` 不保留独立入口；资源、构建、检查和必要试玩由实际任务承担。

## gate 退役

mgs-gate、专用运行服务、角色或任务或用途令牌、运行根、策略配置、强制通道写入及占用审计已从安装包有效能力中移除。普通工作使用宿主和项目已有工具。不保留可选 mgs-gate 或替代权限系统。

项目迁移时，有效配置进入新版对应位置；gate 配置及必要历史证据单独留存，**不得当作新版权限**。退役不等于授权删除资料，也不启停既有长期服务或放宽宿主权限。本说明不替代用户环境迁移核对。

仍有用途的记录、版本核对、草稿及回读继续走 `records/mgs_records.py` 与 provenance 指纹。
