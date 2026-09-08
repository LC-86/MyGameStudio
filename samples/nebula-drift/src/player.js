// 玩家小飞船:移动与推进。
// 注:推进当前按「可二段推进」实现(任务 01 的进行中试验),
// 与 docs/DESIGN_NOTES.md 已采纳的「单次推进」要求不一致,尚待开发者裁决。
const MAX_JUMPS = 2; // 二段推进上限

class Player {
  constructor(x, y) {
    this.x = x;
    this.y = y;
    this.vx = 0;
    this.vy = 0;
    this.jumpsUsed = 0;
    this.score = 0;
  }

  thrust() {
    if (this.jumpsUsed >= MAX_JUMPS) {
      return false; // 二段推进次数用尽,需落地重置
    }
    this.jumpsUsed += 1;
    this.vy = -6.5;
    return true;
  }

  land() {
    this.jumpsUsed = 0; // 落地重置二段推进
  }

  tick(gravity) {
    this.vy += gravity;
    this.x += this.vx;
    this.y += this.vy;
    if (this.y >= 400) {
      this.y = 400;
      this.vy = 0;
      this.land();
    }
  }
}
