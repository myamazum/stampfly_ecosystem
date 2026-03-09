# VPython カメラ Yaw 追従問題

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 状態

- **未解決**（2026-03-09 revert済み、コミット c2cf8bb）
- 対象ファイル: `vpython_backend.py` の `follow_camera_setting()`

## 2. 症状

- ドローンが Yaw 回転しても風景が動かない（カメラが追従しない）
- ±π 境界を跨いだときだけカメラアングルが急に切り替わる
- 画面上でドローンが回転しているのが見える（本来は機体中央固定で風景が流れるべき）
- Windows/Mac では以前動いていた

## 3. 試したアプローチ（全て効果なし）

| # | アプローチ | 結果 |
|---|-----------|------|
| 1 | `scene.camera.pos` / `scene.camera.axis` を毎フレーム設定 | VPython が上書きしている可能性、効果なし |
| 2 | `scene.center` / `scene.forward` / `scene.range` に切替 | 同様に効果なし、画角も変わった |
| 3 | Yaw スムージング（alpha_yaw 0.05〜0.9） | 根本原因ではない |
| 4 | オリジナル stampfly_sim コード（スムージングなし）に完全復元 | それでも動かない |

## 4. 考察

- オリジナル（stampfly_sim）のコードでも動かないため、VPython のバージョンまたは環境依存の問題
- VPython 7.6.5 のカメラ制御が `scene.camera.pos/axis` 設定を無視している疑い
- ブラウザレンダリング（WebGL）側の問題の可能性

## 5. 次のステップ

- 実機でシミュレータを動かしながら print デバッグ
  - `scene.camera.pos` が設定後に実際に反映されているか確認
  - `scene.forward` の値が毎フレーム変わっているか確認
- VPython のバージョン差異（Win/Mac vs Ubuntu）を確認
- Genesis シミュレータ（pygame ベース）のカメラ実装を参考に別アプローチを検討

---

<a id="english"></a>

## 1. Status

- **Unresolved** (reverted on 2026-03-09, commit c2cf8bb)
- Target file: `follow_camera_setting()` in `vpython_backend.py`

## 2. Symptoms

- Scenery does not move when drone yaws (camera does not follow)
- Camera angle snaps only when crossing ±π boundary
- Drone visibly rotates on screen (should stay centered with scenery flowing)
- Previously worked on Windows/Mac

## 3. Approaches Tried (all ineffective)

| # | Approach | Result |
|---|----------|--------|
| 1 | Set `scene.camera.pos` / `scene.camera.axis` every frame | VPython likely overrides, no effect |
| 2 | Switch to `scene.center` / `scene.forward` / `scene.range` | Also no effect, FOV changed |
| 3 | Yaw smoothing (alpha_yaw 0.05–0.9) | Not the root cause |
| 4 | Full revert to original stampfly_sim code (no smoothing) | Still does not work |

## 4. Analysis

- Original stampfly_sim code also fails → VPython version or environment issue
- VPython 7.6.5 camera control may ignore `scene.camera.pos/axis` settings
- Possible browser rendering (WebGL) issue

## 5. Next Steps

- Debug with simulator running, print `scene.camera.pos` / `scene.forward` values
- Compare VPython versions across Win/Mac/Ubuntu
- Consider alternative approach based on Genesis simulator (pygame camera)
