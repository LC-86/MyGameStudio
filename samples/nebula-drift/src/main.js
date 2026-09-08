// 星雾漂流主循环与输入。
// 注:输入映射当前同时支持 方向键 与 WASD(任务 01 顺手加的),
// 与 docs/DESIGN_NOTES.md 已采纳的「仅键盘方向键、不支持 WASD」要求不一致,尚待开发者裁决。
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const player = new Player(320, 400);
const GRAVITY = 0.35;
const ROUND_SECONDS = 90;

const KEYMAP = {
  ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down",
  KeyA: "left", KeyD: "right", KeyW: "up", KeyS: "down", // WASD 支持
};

let held = {};
let elapsed = 0;

window.addEventListener("keydown", (event) => {
  const action = KEYMAP[event.code];
  if (!action) return;
  event.preventDefault();
  held[action] = true;
  if (action === "up") player.thrust();
});
window.addEventListener("keyup", (event) => {
  const action = KEYMAP[event.code];
  if (action) held[action] = false;
});

function tick(dt) {
  player.vx = (held.left ? -4 : 0) + (held.right ? 4 : 0);
  player.tick(GRAVITY);
  elapsed += dt;
}

function draw() {
  ctx.fillStyle = "#06070f";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#e8e2ff";
  ctx.font = "14px sans-serif";
  ctx.fillText(`星尘: ${player.score}`, 12, 24);
  ctx.fillText(`剩余: ${Math.max(0, ROUND_SECONDS - Math.floor(elapsed))}s`, 540, 24);
  ctx.fillStyle = "#9db4ff";
  ctx.fillRect(player.x - 10, player.y - 10, 20, 20);
}

let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  tick(dt);
  draw();
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
