"""
VPython performance diagnostic script
VPython 性能診断スクリプト

Tests:
1. Minimal scene: single box + rate() timing
2. Object count scaling: measure rate() latency as objects increase
"""
import time
from vpython import box, vector, canvas, rate, sphere, color

print("=== VPython Performance Test ===")
print()

# Test 1: Minimal scene with rate() timing
# テスト1: 最小シーンでのrate()タイミング
print("[Test 1] Minimal scene - rate(60) latency")
scene = canvas(title='Performance Test', width=600, height=400)
b = box(pos=vector(0, 0, 0), size=vector(1, 1, 1), color=color.red)

# Warm up
for i in range(5):
    rate(60)

# Measure rate() latency
times = []
for i in range(60):
    t0 = time.perf_counter()
    b.pos = vector(0.01 * i, 0, 0)
    rate(60)
    dt = time.perf_counter() - t0
    times.append(dt)

avg_rate = sum(times) / len(times)
min_rate = min(times)
max_rate = max(times)
print(f"  rate(60) latency: avg={avg_rate*1000:.1f}ms  min={min_rate*1000:.1f}ms  max={max_rate*1000:.1f}ms")
print(f"  Expected: ~16.7ms (60 FPS)")
print(f"  Actual FPS: {1.0/avg_rate:.1f}")
print()

# Test 2: Object count impact
# テスト2: オブジェクト数の影響
print("[Test 2] Object count scaling")
counts = [10, 100, 1000, 5000]
for count in counts:
    # Clear and create new scene
    scene2 = canvas(title=f'Test: {count} objects', width=600, height=400)
    objects = []
    for j in range(count):
        x = (j % 50) * 0.5
        y = (j // 50) * 0.5
        objects.append(box(pos=vector(x, y, 0), size=vector(0.4, 0.4, 0.4),
                          color=vector(0.5, 0.5, 0.5)))

    # Measure rate() with these objects
    test_times = []
    for i in range(20):
        t0 = time.perf_counter()
        objects[0].pos = vector(0.01 * i, 0, 0)
        rate(60)
        dt = time.perf_counter() - t0
        test_times.append(dt)

    avg = sum(test_times) / len(test_times)
    print(f"  {count:5d} objects: rate(60) avg={avg*1000:.1f}ms  FPS={1.0/avg:.1f}")

print()
print("=== Test Complete ===")
