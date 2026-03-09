# VPython カメラ Yaw 追従問題

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 状態

- **修正済み**（2026-03-09）
- 対象ファイル: `vpython_backend.py` の `follow_camera_setting()`, `camera_init()`, `fix_camera_setting()`, `fix_human_setting()`

## 2. 症状（修正前）

- ドローンが Yaw 回転しても風景が動かない（カメラが追従しない）
- ±π 境界を跨いだときだけカメラアングルが急に切り替わる
- 画面上でドローンが回転しているのが見える（本来は機体中央固定で風景が流れるべき）

## 3. 根本原因

VPython のカメラには**プライマリプロパティ**と**派生プロパティ**がある:

| 種別 | プロパティ | 用途 |
|------|-----------|------|
| プライマリ | `scene.center`, `scene.forward`, `scene.range`, `scene.up`, `scene.fov` | カメラを直接制御 |
| 派生 | `scene.camera.pos`, `scene.camera.axis` | プライマリから計算される |

`camera.axis` のセッターが `camera.pos` の**古い値**を参照して `scene.center` を上書きする:

```python
# VPython 内部コード (vpython.py line ~2865)
@axis.setter
def axis(self, value):
    c.center = self.pos + value   # ← 古い pos を使う！
    c.axis = norm(value)
    c.range = mag(value) * tan(c.fov / 2)
```

`camera.pos` → `camera.axis` の順で設定すると **依存関係ループ** が発生し、yaw 方向の変化が正しく反映されなかった。

## 4. 修正内容

全カメラ関数で `camera.pos` / `camera.axis`（派生プロパティ）の使用をやめ、プライマリプロパティのみを使用:

```python
# 修正後
self.scene.center = vector(...)    # 注視点
self.scene.forward = vector(...)   # カメラ方向（正規化）
self.scene.range = d               # カメラ距離
self.scene.up = vector(0, 0, -1)   # 上方向
self.scene.fov = ...               # 視野角
```

## 5. 要確認

- 実機で yaw 操作時にカメラが追従するか目視確認

---

<a id="english"></a>

## 1. Status

- **Fixed** (2026-03-09)
- Target files: `follow_camera_setting()`, `camera_init()`, `fix_camera_setting()`, `fix_human_setting()` in `vpython_backend.py`

## 2. Symptoms (before fix)

- Scenery did not move when drone yawed (camera did not follow)
- Camera angle snapped only when crossing ±π boundary
- Drone visibly rotated on screen (should stay centered with scenery flowing)

## 3. Root Cause

VPython camera has **primary properties** and **derived properties**:

| Type | Properties | Purpose |
|------|-----------|---------|
| Primary | `scene.center`, `scene.forward`, `scene.range`, `scene.up`, `scene.fov` | Direct camera control |
| Derived | `scene.camera.pos`, `scene.camera.axis` | Computed from primary |

The `camera.axis` setter references the **old** `camera.pos` value to overwrite `scene.center`:

```python
# VPython internal code (vpython.py line ~2865)
@axis.setter
def axis(self, value):
    c.center = self.pos + value   # ← uses OLD pos!
    c.axis = norm(value)
    c.range = mag(value) * tan(c.fov / 2)
```

Setting `camera.pos` then `camera.axis` creates a **dependency loop**, preventing yaw changes from being reflected correctly.

## 4. Fix

All camera functions now use primary properties only (no `camera.pos` / `camera.axis` setters):

```python
# After fix
self.scene.center = vector(...)    # look-at point
self.scene.forward = vector(...)   # camera direction (normalized)
self.scene.range = d               # camera distance
self.scene.up = vector(0, 0, -1)   # up direction
self.scene.fov = ...               # field of view
```

## 5. Verification needed

- Visual confirmation that camera follows yaw during live simulation
