// harbor-run 可玩骨架(验收夹具)
const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");
let buoyCount = 0;
window.addEventListener("keydown", (e) => {
  if (e.key === "ArrowUp") buoyCount += 1;
  document.getElementById("c").title = `buoys=${buoyCount}`;
});
function frame() {
  ctx.fillStyle = "#0b1d2a"; ctx.fillRect(0, 0, 480, 320);
  ctx.fillStyle = "#ffd166"; ctx.fillRect(224, 148, 32, 24);
  requestAnimationFrame(frame);
}
frame();
