// 潮池:螃蟹捡贝壳。单文件实现,无构建工具。
// 技术约定见 docs/mygamestudio/TECH_DESIGN.md。

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

const player = { x: 240, y: 160, speed: 120 };
let shellCount = 0;            // 贝壳计数:单一整数,不区分每一枚贝壳
let tideSeconds = 60;          // 距涨潮秒数(任务 02 将实现可视化提示)
const shells = [];             // 场上待拾取的贝壳实体

function spawnShell() {
  shells.push({
    x: 20 + Math.random() * (canvas.width - 40),
    y: 20 + Math.random() * (canvas.height - 40),
  });
}

function collect(shell) {
  const idx = shells.indexOf(shell);
  if (idx >= 0) shells.splice(idx, 1);
  shellCount += 1;             // 拾取即累计;当前没有"掉落回场上"的路径
  document.getElementById("shells").textContent = String(shellCount);
}

function update(dt) {
  // 方向键移动
  if (keys.ArrowLeft) player.x -= player.speed * dt;
  if (keys.ArrowRight) player.x += player.speed * dt;
  if (keys.ArrowUp) player.y -= player.speed * dt;
  if (keys.ArrowDown) player.y += player.speed * dt;
  // 拾取判定
  for (const shell of [...shells]) {
    if (Math.hypot(shell.x - player.x, shell.y - player.y) < 14) collect(shell);
  }
  // 潮汐计时
  tideSeconds = Math.max(0, tideSeconds - dt);
  document.getElementById("tide").textContent = String(Math.ceil(tideSeconds));
}

const keys = {};
window.addEventListener("keydown", (e) => { keys[e.key] = true; });
window.addEventListener("keyup", (e) => { keys[e.key] = false; });

let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  update(dt);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#e8b04b";
  ctx.fillRect(player.x - 10, player.y - 7, 20, 14);
  ctx.fillStyle = "#f3f1e4";
  for (const shell of shells) {
    ctx.beginPath();
    ctx.arc(shell.x, shell.y, 6, 0, Math.PI * 2);
    ctx.fill();
  }
  requestAnimationFrame(frame);
}

for (let i = 0; i < 6; i += 1) spawnShell();
requestAnimationFrame(frame);
