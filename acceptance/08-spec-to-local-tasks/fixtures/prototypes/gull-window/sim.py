#!/usr/bin/env python3
"""海鸥掉落拾回窗口的确定性 Monte Carlo 原型。

事实来源：GAME_DESIGN v2、TECH_DESIGN v1、src/main.js、src/index.html：
画布 480x320、移动速度 120 px/s、拾取判定半径 14 px、正式代码使用
Math.random 且无种子。本原型为可复现而固定 seed=20260908。

模型假设：俯冲点等于玩家当前位置；掉落点在指定散布半径的圆盘内均匀抽样，
超出画布的点裁剪至边界；玩家立刻改向并沿直线最短路径移动。不模拟反应延迟、
障碍、当前输入惯性、潮汐提前结束或浏览器帧率，因此结果是几何可达率上限。
"""

import math
import random

WIDTH = 480
HEIGHT = 320
SPEED = 120.0
PICKUP_RADIUS = 14.0
SEED = 20260908
TRIALS = 5000
WINDOWS = (2.0, 2.5, 3.0, 3.5)
SPREADS = (240.0, 360.0)


def sample_distances(rng, spread):
    distances = []
    for _ in range(TRIALS):
        px = rng.uniform(0.0, WIDTH)
        py = rng.uniform(0.0, HEIGHT)
        radius = spread * math.sqrt(rng.random())
        angle = rng.uniform(0.0, 2.0 * math.pi)
        sx = min(WIDTH, max(0.0, px + radius * math.cos(angle)))
        sy = min(HEIGHT, max(0.0, py + radius * math.sin(angle)))
        distance = math.hypot(sx - px, sy - py)
        distances.append(distance)
    distances.sort()
    return distances


def summarize(distances, window):
    recovered = sum(max(0.0, distance - PICKUP_RADIUS) <= SPEED * window for distance in distances)
    p95 = distances[int(0.95 * (TRIALS - 1))]
    return recovered, 100.0 * recovered / TRIALS, sum(distances) / TRIALS, p95


def main():
    rng = random.Random(SEED)
    print("gull-window deterministic simulation")
    print(f"seed={SEED} trials_per_combo={TRIALS} canvas={WIDTH}x{HEIGHT} speed={SPEED:.0f}px/s pickup_radius={PICKUP_RADIUS:.0f}px")
    print("assumption=immediate straight-line pursuit; uniform disk drop; canvas-clamped")
    print("window_s spread_px recovered/trials recovery_pct mean_distance_px p95_distance_px")
    for spread in SPREADS:
        distances = sample_distances(rng, spread)
        for window in WINDOWS:
            recovered, pct, mean_distance, p95 = summarize(distances, window)
            print(f"{window:>8.1f} {spread:>9.0f} {recovered:>5}/{TRIALS:<5} {pct:>11.2f}% {mean_distance:>16.2f} {p95:>15.2f}")


if __name__ == "__main__":
    main()
