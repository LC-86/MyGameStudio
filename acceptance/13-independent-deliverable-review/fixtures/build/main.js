// 潮池:螃蟹捡贝壳。单文件实现,无构建工具。
// 技术约定见 docs/mygamestudio/TECH_DESIGN.md。

const ROUND_DURATION_SECONDS = 60;
const URGENT_THRESHOLD_SECONDS = 10;
const MAX_FRAME_DELTA_SECONDS = 0.05;
const PICKUP_RADIUS_PX = 14;
const INITIAL_SHELL_COUNT = 6;

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const shellCountElement = document.getElementById("shells");
const tideElement = document.getElementById("tide");
const tideStatusElement = document.getElementById("tide-status");
const tideBarElement = document.getElementById("tide-bar");
const resultElement = document.getElementById("result");
const hudElement = document.getElementById("hud");

const player = { x: 240, y: 160, speed: 120 };
let shellCount = 0;
let remainingSeconds = ROUND_DURATION_SECONDS;
let roundState = "playing";
const shells = [];

// 供后续刷新与掉落系统接入结算边界；本任务不新增持续刷新机制。
let shellSpawnTimer = null;
const activeRecoveries = [];

function spawnShell() {
  if (roundState !== "playing") return false;
  shells.push({
    x: 20 + Math.random() * (canvas.width - 40),
    y: 20 + Math.random() * (canvas.height - 40),
  });
  return true;
}

function collect(shell) {
  if (roundState !== "playing") return;
  const idx = shells.indexOf(shell);
  if (idx < 0) return;
  shells.splice(idx, 1);
  shellCount += 1;
  shellCountElement.textContent = String(shellCount);
}

function updateTideHud() {
  const displaySeconds = Math.ceil(remainingSeconds);
  const remainingRatio = remainingSeconds / ROUND_DURATION_SECONDS;
  const isUrgent = remainingSeconds > 0 && remainingSeconds <= URGENT_THRESHOLD_SECONDS;

  tideElement.textContent = String(displaySeconds);
  tideBarElement.style.width = `${Math.max(0, remainingRatio) * 100}%`;
  tideBarElement.parentElement.setAttribute("aria-valuenow", String(displaySeconds));
  tideStatusElement.classList.toggle("urgent", isUrgent);
  hudElement.classList.toggle("urgent", isUrgent);
  tideStatusElement.textContent = isUrgent ? "即将涨潮！" : "距涨潮";
}

function settleRound() {
  if (roundState === "settled") return;
  roundState = "settled";

  if (shellSpawnTimer !== null) {
    clearInterval(shellSpawnTimer);
    shellSpawnTimer = null;
  }
  activeRecoveries.length = 0;
  for (const key of Object.keys(keys)) keys[key] = false;

  updateTideHud();
  resultElement.hidden = false;
  resultElement.textContent = `潮汐结算：拾取总数 ${shellCount} 枚`;
}

function update(dt) {
  if (roundState !== "playing") return;

  remainingSeconds = Math.max(0, remainingSeconds - dt);
  updateTideHud();
  if (remainingSeconds === 0) {
    settleRound();
    return;
  }

  if (keys.ArrowLeft) player.x -= player.speed * dt;
  if (keys.ArrowRight) player.x += player.speed * dt;
  if (keys.ArrowUp) player.y -= player.speed * dt;
  if (keys.ArrowDown) player.y += player.speed * dt;
  player.x = Math.max(10, Math.min(canvas.width - 10, player.x));
  player.y = Math.max(7, Math.min(canvas.height - 7, player.y));

  for (const shell of [...shells]) {
    if (Math.hypot(shell.x - player.x, shell.y - player.y) < PICKUP_RADIUS_PX) {
      collect(shell);
    }
  }
}

const keys = {};
window.addEventListener("keydown", (event) => { keys[event.key] = true; });
window.addEventListener("keyup", (event) => { keys[event.key] = false; });

let last = performance.now();
function frame(now) {
  const dt = Math.min(MAX_FRAME_DELTA_SECONDS, (now - last) / 1000);
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

for (let i = 0; i < INITIAL_SHELL_COUNT; i += 1) spawnShell();
updateTideHud();
requestAnimationFrame(frame);
