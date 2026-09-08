// 齿轮谜城:章节式推箱子变体。单文件实现,无构建工具。
// 技术约定见 docs/mygamestudio/TECH_DESIGN.md。

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

// 章节关卡数据:每关一个网格字符串(# 墙 . 地 G 目标齿轮槽 B 可推齿轮块 P 起点)
const LEVELS = [
  [
    "#####",
    "#P.B#",
    "#..G#",
    "#####",
  ],
  [
    "######",
    "#P...#",
    "#.B..#",
    "#..G.#",
    "######",
  ],
];

let levelIndex = 0;
let steps = 0;
const state = { player: { x: 1, y: 1 }, blocks: [], goals: [] };

function loadLevel(index) {
  const grid = LEVELS[index];
  state.blocks = [];
  state.goals = [];
  grid.forEach((row, y) => {
    [...row].forEach((cell, x) => {
      if (cell === "P") state.player = { x, y };
      if (cell === "B") state.blocks.push({ x, y });
      if (cell === "G") state.goals.push({ x, y });
    });
  });
  steps = 0;
  document.getElementById("level").textContent = String(index + 1);
}

function isWall(x, y) {
  const row = LEVELS[levelIndex][y];
  return !row || row[x] === "#" || row[x] === undefined;
}

function tryMove(dx, dy) {
  const nx = state.player.x + dx;
  const ny = state.player.y + dy;
  if (isWall(nx, ny)) return;
  const block = state.blocks.find((b) => b.x === nx && b.y === ny);
  if (block) {
    const bx = nx + dx;
    const by = ny + dy;
    if (isWall(bx, by) || state.blocks.some((b) => b.x === bx && b.y === by)) return;
    block.x = bx;
    block.y = by;
  }
  state.player.x = nx;
  state.player.y = ny;
  steps += 1;
  document.getElementById("steps").textContent = String(steps);
  checkSolved();
}

function checkSolved() {
  const solved = state.goals.every((g) =>
    state.blocks.some((b) => b.x === g.x && b.y === g.y));
  if (solved) {
    // 过关:装饰性的火花方向用随机(与玩法无关);关卡顺序固定
    const sparkAngle = Math.random() * Math.PI * 2;
    console.log("solved", levelIndex + 1, "spark", sparkAngle.toFixed(2));
    if (levelIndex + 1 < LEVELS.length) loadLevel(levelIndex + 1);
  }
}

window.addEventListener("keydown", (e) => {
  if (e.key === "ArrowLeft") tryMove(-1, 0);
  if (e.key === "ArrowRight") tryMove(1, 0);
  if (e.key === "ArrowUp") tryMove(0, -1);
  if (e.key === "ArrowDown") tryMove(0, 1);
});

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const cell = 48;
  const grid = LEVELS[levelIndex];
  grid.forEach((row, y) => {
    [...row].forEach((cellChar, x) => {
      if (cellChar === "#") {
        ctx.fillStyle = "#4a4a55";
        ctx.fillRect(x * cell, y * cell, cell, cell);
      }
    });
  });
  ctx.fillStyle = "#c8a24a";
  for (const g of state.goals) ctx.fillRect(g.x * cell + 12, g.y * cell + 12, cell - 24, cell - 24);
  ctx.fillStyle = "#8a8a95";
  for (const b of state.blocks) ctx.fillRect(b.x * cell + 6, b.y * cell + 6, cell - 12, cell - 12);
  ctx.fillStyle = "#e0d6b8";
  ctx.fillRect(state.player.x * cell + 14, state.player.y * cell + 14, cell - 28, cell - 28);
  requestAnimationFrame(draw);
}

loadLevel(0);
requestAnimationFrame(draw);
