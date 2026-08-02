# Bitcraze Crazyflie エコシステム到達点調査（拡張デッキ・測位方式）

調査日: 2026-08-02
方法: bitcraze.io（製品ページ・公式ドキュメント・公式ブログ）、GitHub（bitcraze/*, USC-ACTLab/crazyswarm, imrclab/crazyswarm2）を WebFetch で直接確認。一部は WebSearch のスニペット要約であり、その旨を明記した（一次情報を直接 WebFetch で確認できていないもの）。
凡例: 「確認済」= WebFetchで一次情報を直接読んだ。「未確認」= 情報源に到達できず、または記載がなかった。

---

## 1. Flow deck v2

**出典:** https://www.bitcraze.io/products/flow-deck-v2/ （確認済）、 https://www.bitcraze.io/documentation/tutorials/getting-started-with-flow-deck/ （確認済）

| 項目 | 値 |
|---|---|
| センサー構成 | VL53L1x ToF（対地距離）+ PMW3901 光学フローセンサー（水平移動検出） |
| 測距レンジ | 最大4m |
| 精度 | 「数mm以内（表面・照度条件に依存）」（公称、cm/mm単位の定量的な誤差値の記載なし） |
| 動作高度範囲 | 0.2m〜3.0m（Flow deck v1 / Z-ranger deck v1は1.0mまで） |
| 重量・寸法 | 1.6g、21×28×4mm |
| 対応機体 | Crazyflie 2.X |
| 価格 | $55.00（Bitcraze Store、調査時点で一時的に在庫切れ） |
| 既知の制約 | 光学フローはカメラ方式のため無地・マット面でない床では性能低下。円錐状の検出範囲のため、高度が高いほど誤検出（壁までの距離を報告等）が起きやすい |
| 水平方向の絶対精度公称値 | **未確認**（公式ページ・ドキュメントとも定量的なcm精度の記載なし。光学フローは相対測定のためドリフトが生じる旨のみ記載） |

Flow deck v2 は「Crazyflieの測位方式」比較ページ（後述セクション7参照）には掲載されておらず、絶対位置測位システムではなく相対速度推定センサーとして扱われている点に注意。

---

## 2. Loco Positioning System（UWB）

**出典:** https://www.bitcraze.io/documentation/system/positioning/loco-positioning-system/ （確認済）、https://www.bitcraze.io/documentation/system/positioning/max-range-loco/ （確認済）、https://store.bitcraze.io/products/loco-positioning-deck （確認済）

| 項目 | 値 |
|---|---|
| 使用チップ | Decawave DWM1000（DW1000系UWBモジュール） |
| DW3000/DWM3000への移行 | **未確認**（Bitcraze公式フォーラムに「DWM3000はピン互換で移行しやすい」という議論スレッドがあるのみで、製品化・公式ロードマップは確認できず。https://forum.bitcraze.io/viewtopic.php?t=4430 ） |

### 測位モード別の到達点

| モード | 精度公称 | 同時測位可能機体数 | アンカー数上限 |
|---|---|---|---|
| TWR (Two Way Ranging) | 「10cm程度の範囲」 | **1機のみ** | 最大8（最小4、推奨6） |
| TDoA 2 | TWRと同等 | 複数機（スウォーム向け） | 最大8（固定タイムスロット） |
| TDoA 3 | TDoA 2と同等 | 複数機 | 制限なし（ランダム送信方式、動的追加・削除対応） |

### レンジ実測（公式検証記事）
出典: https://www.bitcraze.io/documentation/system/positioning/max-range-loco/ （確認済）
- 屋内標準設定: 8〜16m（アンテナ方向による）
- 屋外標準設定+スマートパワー: 15m
- 屋外フル送信電力: 50〜70m
- 「科学的検証というより参考値」と明記されている

### カバレッジ（測位方式比較表より）
出典: https://www.bitcraze.io/documentation/system/positioning/ （確認済）
- 最大カバー範囲: **50×50m**、精度は「dm（分米=10cm)オーダー」

### 群飛行の実績（Loco固有）
出典: https://www.bitcraze.io/2016/11/first-crazyflie-swarm-flying-with-tdoa-in-loco-positioning-sytem/ （タイトルのみWebSearchで確認、本文未フェッチ）
- 2016年11月、TDoA方式で**5機のCrazyflie 2.0**の同時群飛行を初めて達成、とWebSearchスニペットに記載。TDoA3では「任意数のタグ」に対応するとドキュメントに明記されているが、**大規模群（数十機規模）での実測・実演の数値は未確認**（Loco Positioning固有の群数記録は見つからず。大規模群の実演は主にモーションキャプチャ環境＝後述Crazyswarmで報告されている）。

| 価格 | $95.00（Loco positioning deck、Bitcraze Store） |

---

## 3. Lighthouse Positioning System

**出典:** https://www.bitcraze.io/products/lighthouse-positioning-deck/ （確認済）、https://www.bitcraze.io/documentation/system/positioning/ligthouse-positioning-system/ （確認済）、https://www.bitcraze.io/2021/05/lighthouse-positioning-accuracy/ （確認済）、https://www.bitcraze.io/documentation/system/positioning/ （確認済）

| 項目 | 値 |
|---|---|
| 使用チップ | TS4231 赤外線受光素子 ×4 + ICE40UP5K FPGA（信号処理） |
| 対応基地局 | HTC Vive / SteamVR Base Station V1・V2の両対応。V2推奨。ファームウェアは既定で**最大4基地局**まで対応 |
| 必要基地局数 | 最低2台 |
| 基地局視野角（V2） | 水平150°、垂直110° |
| 3.3Vシステムとの互換性 | 出荷時点で非互換（最大信号レベル3V） |
| 価格 | $95.00（Bitcraze Store） |

### 精度公称値（食い違いに注意）
- 公式ドキュメント記載: **相対精度 <1mm、絶対精度 <10cm**（5×5m空間での測定。基地局直下50cm以内で最適）（https://www.bitcraze.io/documentation/system/positioning/ligthouse-positioning-system/ 、確認済）
- 測位方式比較表（同ドキュメント群内の別ページ）記載: 最大カバー範囲**8×8×3m**、精度「mm（ミリ）オーダー」（https://www.bitcraze.io/documentation/system/positioning/ 、確認済）
  → 上記2つの数値（5×5m vs 8×8×3m）は出典ページが異なり、Bitcraze公式内でも表現に幅がある。**厳密な最大カバー範囲は未確定**として扱うのが妥当。

### 独立検証（モーションキャプチャとの比較、査読研究）
出典: https://www.bitcraze.io/2021/05/lighthouse-positioning-accuracy/ （確認済、arXiv:2104.11523・ICRA2021ワークショップ発表の論文に基づく）
- Active Marker DeckとMoCapを同時搭載し、Lighthouse V1/V2それぞれをMoCapとの比較でグラウンドトゥルース評価
- **平均・中央値ユークリッド誤差 約2〜4cm**（MoCapとの比較）
- トラッキング空間サイズ・ジッター量・同時検証機数は、このブログ記事内には**記載なし（未確認）**

---

## 4. AI deck（GAP8・オンボードNN）

**出典:** https://www.bitcraze.io/products/ai-deck/ （確認済）、https://github.com/bitcraze/aideck-gap8-examples （確認済、README詳細部は取得不可）、https://www.bitcraze.io/2019/05/pulp-dronet-open-source-and-open-hardware-artificial-intelligence-for-fully-autonomous-navigation-on-crazyflie/ （WebSearch要約、本文未フェッチ）、https://www.bitcraze.io/tag/obstacle-avoidance/ （確認済）

| 項目 | 値 |
|---|---|
| メインAIチップ | GAP8（8+1コア RISC-V、超低消費電力MCU、GreenWaves Technologies製） |
| WiFi/通信 | ESP32（NINA-W102モジュール） |
| カメラ | Himax HM01B0、320×320モノクロ、超低消費電力 |
| メモリ | HyperFlash 512Mbit、HyperRAM 64Mbit |
| 価格 | $240.00（AI-deck 1.1、Bitcraze Store） |
| 制約 | JTAGプログラマ必須、組込み開発の知識推奨、WiFiアンテナが物理的に脆弱 |

### Bitcraze公式リポジトリ（aideck-gap8-examples）に含まれるサンプル
確認済（GitHub該当ページ・ドキュメントミラーより）:
- Hello World Example（GAP8開発の入門例）
- Classification Demo（画像分類）
- Face detection example（顔検出）
- Testing the Himax Camera（カメラ動作確認）
- WiFi Video Streamer（WiFi経由映像ストリーミング）
- Send character over UART / STM-GAP8 CPX communication Example（通信基盤）

これら公式サンプル自体は開発基盤の実演であり、**自律航行そのものを完結させるサンプルは公式リポジトリのトップレベルには含まれていない**（未確認＝より詳しいディレクトリ構成は探索できず）。

### 第三者研究による実証（AI deckを土台に使用、Bitcraze公式ブログでも紹介）
1. **PULP-DroNet**（ETHチューリッヒ／ボローニャ大学、Bitcraze公式ブログ2019年5月で紹介）
   出典: https://www.bitcraze.io/2019/05/pulp-dronet-open-source-and-open-hardware-artificial-intelligence-for-fully-autonomous-navigation-on-crazyflie/ （WebSearch要約。本文の直接WebFetchは未実施のため詳細数値は準一次情報扱い）
   - Crazyflie 2.0上でCNN（DroNetベース）をオンボード実行し、廊下・通路追従＋障害物回避のクローズドループ完全自律飛行を実演
   - 消費電力64〜284mW、6〜18フレーム/秒でのCNN推論
2. **NanoFlowNet**（TUデルフト、Cyber Zoo屋内飛行場での実演）
   出典: WebSearch要約（Bitcraze obstacle-avoidanceタグページには本記事は掲載されておらず、詳細記事URLは未確認）
   - オプティカルフローに基づく左右バランス制御でヨーにより障害物回避、開放環境・雑然環境双方で実演
3. **Multi-zone depth sensorによる自律航行研究**（ETHチューリッヒ、2022年9月、Bitcraze公式ブログに掲載）
   出典: https://www.bitcraze.io/tag/obstacle-avoidance/ 経由で存在確認（確認済）
   - ※この研究はAI deckではなく、STMicroelectronics製マルチゾーンToFセンサーを用いた**独自デッキ**を使用（AI deckとは別物である点に注意）
   - 計算負荷0.31%、レイテンシ210µs、実験飛行で最大212mの飛行距離・信頼性100%と報告

---

## 5. Multi-ranger / Z-ranger / その他デッキ一覧

### Multi-ranger deck
出典: https://www.bitcraze.io/products/multi-ranger-deck/ （確認済）
- センサー: VL53L1x ToF ×5（前・後・左・右・上の5方向）
- レンジ: 最大4m、精度「数mm以内」
- 重量2.3g、35×35×5mm、価格$95.00
- 障害物検知・マッピング・探索実験向け。**衝突回避は初期状態では無効**（アプリ側実装が必要）

### Z-ranger deck / Z-ranger deck v2
出典: https://www.bitcraze.io/products/z-ranger-deck-v2/ （確認済）、Bitcraze Store（確認済）
- v2はVL53L1x ToF、最大4m測距、「数mm以内」精度、1.6g、21×28×4mm
- 用途: 対地高度を一定に保つ自動飛行（階段状の地形にも追従）
- 価格: v1 $18.00、v2 $23.00（v2は調査時点で一時的に在庫切れ）

### Motion Capture Marker Deck
出典: https://www.bitcraze.io/products/motion-capture-marker-deck/ （確認済）
- Qualisysと共同開発。M3ネジ穴35個（5mm間隔）、6.5mm反射マーカー推奨
- 重量1.6g、65×3×65mm、価格$6.50

### Bitcraze Store 掲載デッキ一覧（全20製品、確認済）
出典: https://store.bitcraze.io/collections/decks

| # | 製品名 | 価格 |
|---|---|---|
| 1 | Active marker deck | $150.00 |
| 2 | AI-deck 1.1 | $240.00 |
| 3 | BigQuad deck | $9.00 |
| 4 | Breakout deck | $5.50 |
| 5 | Buzzer deck | $11.00 |
| 6 | Crazyflie Color LED Deck – Bottom Mounted | $23.00 |
| 7 | Crazyflie Color LED Deck – Top Mounted | $23.00 |
| 8 | Female deck connector | $2.50 |
| 9 | Flow deck v2 | $55.00（在庫切れ） |
| 10 | LED-ring deck | $23.00 |
| 11 | Lighthouse positioning deck | $95.00 |
| 12 | Loco positioning deck | $95.00 |
| 13 | Long Pins (15+4+6mm) | $2.00 |
| 14 | Motion capture marker deck | $6.50 |
| 15 | Multi-ranger deck | $95.00 |
| 16 | Prototyping deck | $5.50 |
| 17 | Qi 1.2 wireless charging deck | $38.00（在庫切れ） |
| 18 | SD-card deck | $11.00 |
| 19 | Z-ranger deck | $18.00 |
| 20 | Z-ranger deck v2 | $23.00（在庫切れ） |

Active marker deck（$150）はモーションキャプチャ用のアクティブ（能動発光）マーカーデッキで、Lighthouse精度検証ブログでもグラウンドトゥルース取得に使用されていた。

---

## 6. 群飛行の実績（Crazyswarm等）

### Crazyswarm（初代）
出典: https://dl.acm.org/doi/10.1109/icra.2017.7989376 、 https://whoenig.github.io/publications/2017_ICRA_Preiss_Hoenig.pdf （論文タイトル・書誌情報はWebSearchで確認。本文はWebFetch未実施）、GitHub README（https://github.com/USC-ACTLab/crazyswarm 、確認済だが群数の記載なし）
- 論文: Preiss, Hönig, Sukhatme, Ayanian, "Crazyswarm: A Large Nano-Quadcopter Swarm", ICRA 2017
- WebSearch要約によれば**49機のCrazyflieを3台のCrazyradioで同時飛行**させ、4層構造の回転ピラミッド編隊（底面3m×3m、機体間隔0.5m）を実演
- 測位: Vicon モーションキャプチャシステムを使用
- 無線容量の制約: 1台のCrazyradioあたり推奨3〜4機、理想条件下で最大15機程度
- **注記: 「49機」の具体的数値は論文本文を直接WebFetchで確認できておらず、WebSearchスニペット経由の情報。一次情報（論文PDFそのもの）での裏取りは未実施**

### Crazyswarm2（後継、現行）
出典: https://imrclab.github.io/crazyswarm2/ （確認済）
- ROS 2ベースのスタック。対応機体: Crazyflie 2.1(+)、Crazyflie 2.1 Brushless、Flapper Nimble+、Crazyflie Bolt採用のカスタム機
- Crazyswarm（初代）は現在「非アクティブメンテナンス」状態で、Crazyswarm2への移行が公式に推奨されている
- **Crazyswarm2自体で実証された最大同時飛行機数は未確認**（トップページには記載なし。Overview/Usageページの深掘りは未実施）

---

## 7. モーションキャプチャ統合

出典: https://www.bitcraze.io/documentation/system/positioning/ （確認済）、https://www.bitcraze.io/products/motion-capture-marker-deck/ （確認済）

- 対応システムとして明記: **Qualisys、Vicon、OptiTrack**
- 処理方式: **オフボード**（外部PC側で位置計算し、無線でCrazyflieにフィードバック）— Loco/Lighthouseがオンボード処理であるのと対照的
- 精度: 比較表上は「mm（ミリ）オーダー」、カバレッジは「無制限」と記載
- セットアップ難易度は比較表で「困難」、コストは「$$$」（3方式中最高）と評価されている
- Motion Capture Marker Deck（$6.50）で反射マーカーを機体に取付、Active Marker Deck（$150）で能動発光マーカー方式にも対応

---

## 8. 各測位方式の位置制御精度（公称・報告値まとめ）

出典: https://www.bitcraze.io/documentation/system/positioning/ の比較表（確認済）＋各方式の個別ページ（確認済）

| 測位方式 | 精度（公称） | 精度（独立検証・報告値） | カバレッジ | 処理位置 | 同時機体数 |
|---|---|---|---|---|---|
| Flow deck v2（相対） | 「数mm」（センサー単体の分解能。絶対位置精度の公称なし） | **未確認** | 単機、対地高度0.2-3.0m | オンボード | 1機（相対推定のため群位置管理には非対応） |
| Loco Positioning（TWR/TDoA） | 「10cm程度」（dmオーダー） | **未確認**（独立の定量検証記事は未発見） | 最大50×50m | オンボード | TWR=1機、TDoA2/3=複数機 |
| Lighthouse | 相対<1mm／絶対<10cm（公式）。カバレッジは資料により5×5m〜8×8×3mと幅あり | **平均・中央値ユークリッド誤差 約2〜4cm**（MoCap比較、arXiv:2104.11523、ICRA2021ワークショップ） | 5×5m〜8×8×3m（出典間で不一致、要再確認） | オンボード | 複数機（基地局は既定最大4台の共有インフラ、機体数自体の上限記載なし） |
| モーションキャプチャ | mmオーダー（公式比較表） | ゲイン検証で他方式の「グラウンドトゥルース」として使用される精度 | 無制限（カメラ設置範囲次第） | オフボード | 良好（Crazyswarmで49機実演、ただし本文未裏取り） |

**総括的な未確認事項:**
- Flow deck v2の絶対位置制御精度（cm単位）の公式数値
- Loco Positioning Systemの独立検証によるcm単位精度（公式「10cm程度」の裏取り一次データ）
- Lighthouseの正確なカバレッジ上限（5×5m系と8×8×3m系の記載の不一致）
- Crazyswarm「49機」の論文原文での直接確認（WebSearch経由の二次情報にとどまる）
- Crazyswarm2固有の最大実証機数
- Loco Positioning Systemでの大規模群（数十機）実演の有無・機数
- DW3000/DWM3000への製品移行時期・公式ロードマップ

---

## 出典一覧（本報告で直接WebFetchしたURL）

- https://www.bitcraze.io/products/flow-deck-v2/
- https://www.bitcraze.io/documentation/tutorials/getting-started-with-flow-deck/
- https://www.bitcraze.io/documentation/system/positioning/loco-positioning-system/
- https://www.bitcraze.io/documentation/system/positioning/loco-positioning-system/#twr-and-tdoa
- https://www.bitcraze.io/documentation/system/positioning/max-range-loco/
- https://www.bitcraze.io/documentation/system/positioning/
- https://www.bitcraze.io/documentation/system/positioning/ligthouse-positioning-system/
- https://www.bitcraze.io/products/lighthouse-positioning-deck/
- https://www.bitcraze.io/2021/05/lighthouse-positioning-accuracy/
- https://www.bitcraze.io/products/ai-deck/
- https://github.com/bitcraze/aideck-gap8-examples
- https://www.bitcraze.io/tag/obstacle-avoidance/
- https://www.bitcraze.io/products/multi-ranger-deck/
- https://www.bitcraze.io/products/z-ranger-deck-v2/
- https://www.bitcraze.io/products/motion-capture-marker-deck/
- https://store.bitcraze.io/collections/decks
- https://github.com/USC-ACTLab/crazyswarm
- https://github.com/USC-ACTLab/crazyswarm/blob/master/README.md
- https://imrclab.github.io/crazyswarm2/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/loco-positioning-system/tdoa3_hybrid_mode/
- https://www.bitcraze.io/documentation/repository/aideck-gap8-examples/master/

補助的にWebSearch（スニペット要約のみ、一次本文未フェッチ）で参照した情報源:
- https://dl.acm.org/doi/10.1109/icra.2017.7989376（Crazyswarm論文書誌）
- https://whoenig.github.io/publications/2017_ICRA_Preiss_Hoenig.pdf（Crazyswarm論文PDF、書誌確認のみ）
- https://www.bitcraze.io/2025/06/exploring-the-swarming-potential-of-the-crazyflie/
- https://www.bitcraze.io/2019/05/pulp-dronet-open-source-and-open-hardware-artificial-intelligence-for-fully-autonomous-navigation-on-crazyflie/
- https://www.bitcraze.io/2016/11/first-crazyflie-swarm-flying-with-tdoa-in-loco-positioning-sytem/
- https://forum.bitcraze.io/viewtopic.php?t=4430（DWM3000移行の議論スレッド）
