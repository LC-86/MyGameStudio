# 安全问题报告

请把安全问题与凭据泄漏当成私密报告，不要发到公开 Issue、讨论区或拉取请求。

## 如何报告

1. 优先使用 GitHub 私密漏洞报告：
   [创建私密 advisory](https://github.com/LC-86/MyGameStudio/security/advisories/new)
2. 若该入口尚未开启或无法提交，通过 GitHub 用户
   [LC-86](https://github.com/LC-86) 发送**不含凭据**的联系说明，等待维护者给出私密通道。
3. 不要编造或使用未公布的邮箱。本仓库目前没有单独的安全邮箱。

## 报告时请包含

- 技能库版本（`VERSION`，例如 3.0.1）与安装方式（官方 `skills` CLI，完整安装或子集安装）
- `skills` CLI 版本（`npx skills@latest --version`）、宿主或 Agent 名称与版本、操作系统
- 涉及的技能（20 项之一，例如 `setup-gamestudio`）
- 去凭据后的复现步骤与影响范围
- 是否涉及同名技能多源安装（例如另装了 Matt 原版技能库或旧版 MyGameStudio）

## 不要发送

- 访问令牌、API 密钥、账号密码、`auth.json` 或 cookie
- 未脱敏的用户游戏项目、私人对话或未授权素材
- 可直接用于未授权访问的完整原始日志

维护者收到报告后会确认影响范围，并在修复可用时说明受影响版本与升级方式。
