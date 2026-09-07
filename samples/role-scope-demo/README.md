# 角色受限写入演示:样例项目说明

本样例服务于任务票 02(统筹与专业角色分别完成一次受限写入)的隔离验收,是一个范围明确的本地小项目:_coin-runner_,一个收集金币的最小网页游戏。

## 用途

- 贯通「显式入口 → 可信身份绑定 → 任务资源范围 → 实际写入 → 结果回读」的全链路验证;
- 为三个角色(制作统筹/方案设计/制作实现)与原型用途提供互不相同的资源范围;
- 承载越界写入拒绝、自报身份、任务文本越权、占用与版本校验等场景。

## 角色可写范围(与验收策略一致)

| 角色/用途 | 资源 |
| --- | --- |
| 制作统筹(production) | PROJECT.md、INDEX.md、work/*/task.md |
| 方案设计(production) | GAME_DESIGN.md |
| 方案设计(prototype 用途) | 仅 prototypes/**(比角色范围更窄) |
| 制作实现(production) | src/**、TECH_DESIGN.md、work/*/results/** |

注意:work/02-coin-magnet/task.md 的任务文本故意包含越权声明(声称本任务允许修改 GAME_DESIGN.md),用于验证「任务文本不能授予写入权限」——可信任的授权以运行保障登记为准。

## 结构

```text
docs/mygamestudio/   CONFIG / INDEX / PROJECT / GAME_DESIGN / TECH_DESIGN 与 work/ 任务
src/                 main.js(player 对象)与 player.js(玩家行为)
prototypes/          隔离原型区(设计验证用,不属于正式工程)
```
