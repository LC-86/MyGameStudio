// 主循环与输入接线(任务 01-player-move 交付)。
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const keys = {};
addEventListener("keydown", (e) => {
  keys[e.key] = true;
  if (e.key === " ") player.jump();
});
addEventListener("keyup", (e) => {
  keys[e.key] = false;
});

const player = new Player(40, 300);
let last = performance.now();

function frame(now) {
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  player.handleInput(keys);
  player.update(dt, 320);
  ctx.fillStyle = "#222";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#4caf50";
  ctx.fillRect(0, 320, canvas.width, 40);
  ctx.fillStyle = "#ffca28";
  ctx.fillRect(player.x, player.y - 20, 20, 20);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
