# atlas-drop:当前技术设计

维护责任:制作实现。基线版本:v1。产品依据:GAME_DESIGN v1。

## 工程现状与限制

单文件 ES 模块 src/main.js,无构建步骤、无外部依赖;验证用 node 直接导入运行。

## 本轮实现约定

- 模块职责与接口:state 为唯一可变状态;onTick/onCollect 为入口函数。
- 数据、状态与资源:回合状态 {score, time};护盾为 state.shield(01 新增)。
- 运行与构建:node --input-type=module 或测试脚本导入。
- 关键限制:无渲染层,行为以状态断言验证。

## 验证方法

无头状态检查:导入模块、驱动 onTick/onCollect、断言状态变化;检查记录落任务 results/。

## 取舍与变化

(暂无)
