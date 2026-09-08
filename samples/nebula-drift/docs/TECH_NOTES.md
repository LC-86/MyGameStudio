# 星雾漂流:技术笔记

维护:开发者本人(技术)。

## 现状

- 零依赖纯 HTML/JS;浏览器直接打开 src/index.html 即玩。
- 代码:src/main.js(主循环与输入)、src/player.js(玩家与推进)。
- 资源:assets/sprites/(SVG 占位图)。
- 工程:package.json 仅提供 serve 脚本(python3 -m http.server),无构建、无依赖。

## 验证方法

- 手动:浏览器打开 src/index.html,方向键试玩一局。
