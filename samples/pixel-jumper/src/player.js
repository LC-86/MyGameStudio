// 玩家实体:左右移动、重力、二段跳。
// 来源:任务 01-player-move(2026-09-06)与 02-double-jump(2026-09-07)。
class Player {
  constructor(x, y) {
    this.x = x;
    this.y = y;
    this.vx = 0;
    this.vy = 0;
    this.jumpsUsed = 0;
    this.onGround = false;
  }

  handleInput(keys) {
    const speed = 220; // px/s,允许 ±10% 调整
    this.vx = 0;
    if (keys.ArrowLeft) this.vx = -speed;
    if (keys.ArrowRight) this.vx = speed;
  }

  jump() {
    if (this.onGround) {
      this.vy = -520;
      this.jumpsUsed = 1;
      this.onGround = false;
    } else if (this.jumpsUsed < 2) {
      // 二段跳:仅在空中且本轮未使用第二次跳跃
      this.vy = -460;
      this.jumpsUsed = 2;
    }
  }

  update(dt, groundY) {
    this.x += this.vx * dt;
    this.vy += 1400 * dt; // 重力
    this.y += this.vy * dt;
    if (this.y >= groundY) {
      this.y = groundY;
      this.vy = 0;
      this.onGround = true;
      this.jumpsUsed = 0; // 落地重置
    }
  }
}
