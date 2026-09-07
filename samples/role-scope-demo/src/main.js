// 金币跑者:游戏主循环(最小占位实现)
const canvas = document.createElement('canvas');
canvas.width = 640; canvas.height = 480;
document.body.appendChild(canvas);
const ctx = canvas.getContext('2d');

const player = { x: 320, y: 400, r: 12, collectedCallback: null };
const coins = [
  { x: 100, y: 240, r: 12 },
  { x: 220, y: 240, r: 12 },
  { x: 320, y: 240, r: 12 },
  { x: 420, y: 240, r: 12 },
  { x: 520, y: 240, r: 12 },
];
let collected = 0;

function loop() {
  // 主循环占位:移动与收集逻辑由 player.js 提供
  requestAnimationFrame(loop);
}
loop();
