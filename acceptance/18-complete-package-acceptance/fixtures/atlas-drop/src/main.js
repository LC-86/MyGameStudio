// atlas-drop 最小骨架:60 秒一局,左右操控收集器。
const ROUND_SECONDS = 60;
const state = { score: 0, time: ROUND_SECONDS };

function startRound() {
  state.score = 0;
  state.time = ROUND_SECONDS;
}

function onTick() {
  state.time = Math.max(0, state.time - 1);
}

function onCollect(stardust) {
  state.score += stardust.value;
}

export { ROUND_SECONDS, state, startRound, onTick, onCollect };
