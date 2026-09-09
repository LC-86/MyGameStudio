# 后端切换确认(开发者,2026-09-09T12:02:22+08:00)

1. 确认迁移清单(switch-plan.json):两个既有任务迁往 GitHub Issues,身份保持
   01-harbor-timer / 02-crane-sprite;旧本地记录保留为只读历史。
2. 确认远端写入授权:仅对测试仓库 github.com/mygamestudio/issue-accept 授权任务与结果读写(issues-write),
   记入 CONFIG 外部访问行;仅选择 GitHub 后端不构成授权,其余仓库一律未授权。
3. 核心设计文档(PROJECT/GAME_DESIGN/TECH_DESIGN)保留本地 Markdown 位置,
   不复制进 Issue;本轮远端执行者仅经本地替身可见,基线引用不可达如实保留,
   不宣称未发布本地资料已可远端访问。
4. 切换生效后 docs/mygamestudio/work/ 不再是当前任务来源(唯一当前来源);
   新 CONFIG 由统筹在会话内经受控通道写入。
