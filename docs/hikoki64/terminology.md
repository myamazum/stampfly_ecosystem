# 原稿用語対訳リスト（日本語論文の慣用検証済み）

第64回飛行機シンポジウム原稿「StampFlyの位置制御に関する一考察」用。
2026-08-01 に J-STAGE・CiNii・学会講演概要集の実例検索で検証（検証方法:
各表記候補で実在論文を検索し、ヒットした表記のみ「慣用」と判定）。
**執筆時はこの表に従う。表にない専門用語を新たに使う場合は、使う前に同じ方法で検証して本表に追記する。**

## 採用表記（検証済み）

| 概念 | 採用表記 | 根拠（実在例） | 備考 |
|------|---------|---------------|------|
| 機体分類 | クアッドロータ（quadrotor）※初出で英語併記 | SICE論文集50-11(2014)「クアッドロータヘリコプタの適応H∞追従制御」ほか | クワッドロータ/クアッドコプタ等の揺れ大。初出定義後に統一使用 |
| 無人機の総称 | 無人航空機（ドローン）※初出併記、以後「機体」等で受ける | 計測と制御56-1(2017)「無人航空機システム(ドローン)の歴史と技術発展」 | 本文で「ドローン」単独は避ける |
| 超小型級 | 超小型（＋クアッドロータ） | 日本機械学会誌117-1143「超小型飛行ロボット」、JJSASS 64-10「MAV」 | MAV は航空宇宙学会系で英字慣用 |
| GPS が使えない環境 | **非GPS環境** | 計測と制御56-1(2017) 鈴木智「非GPS環境における小型無人航空機の自律制御」ほか計4件 | 「GPS非利用環境」は実例未発見 |
| 光学式流れセンサ | オプティカルフロー／オプティカルフローセンサ（中黒なし） | ROBOMECH2014 2A2-C02 大滝・岩倉・野波「オプティカルフローセンサを用いたUAVの飛行制御」 | 中黒入りは少数派 |
| ToF 測距 | ToF（Time of Flight）測距センサ ※初出併記 | 機械学会中四国支部2021「ToFセンサー…」、計測と制御59-5「TOFセンサ」 | 大文字/小文字の揺れあり→初出併記で吸収 |
| 位置を保つ制御 | 位置制御／位置保持制御／ホバリング | 流体工学部門2022「クアッドロータドローンの位置・姿勢制御」ほか | **「定点保持」は学術実例未発見→使わない** |
| 実際に効くゲイン | **「実効ゲイン」は慣用実例未発見**。説明的表現（「実際に得られる応答のゲイン」）とし、4章で初出定義してから用語として使う | 制御分野でのJ-STAGE実例なし（近縁の確立語は記述関数法の「等価ゲイン」だが本件は非該当） | 1章では説明的表現のみ |
| パラメータを求める | システム同定／パラメータ同定／同定 | 計測と制御47-11 足立修一ほか | 「飛行データに基づく同定」の組み立ては可 |
| 頑健性 | ロバスト性／ロバスト設計／ロバスト安定 | 多数（ROBOMECH2013「クアッドコプターの…ロバスト制御」等） | 問題なし |
| Software-in-the-Loop | **SILS（Software In the Loop Simulation）** ※初出併記 | 第57回自動制御連合講演会(2014) 組込み系SILS | 「SILシミュレーション」は実例未確認 |
| SITL | **一般語としては使わない**。ArduPilot/PX4のシミュレータに言及する場合のみ固有名として（例:「ArduPilotのSITL」） | SITLはArduPilot/PX4エコシステムのツール呼称。学術文献での出現もツール名言及がほぼ全て（2026-08-02判断） | 概念はSILS/SILで表す |
| 多重ループ制御 | カスケード制御／カスケード構造 | 計測と制御1-2(1954)以来の確立語 | 問題なし |
| 慣性センサ | 慣性計測装置（IMU）※初出併記、以後 IMU | 日本船舶海洋工学会論文集21ほか | 問題なし |
| 飛行記録 | **飛行データ** | KJSASS 54-628「飛行データを伝送」 | 「飛行ログ」は学術実例未確認→使わない |

## 参考文献（実在確認済み・書誌）

| ラベル | 書誌 | 状態 |
|--------|------|------|
| honegger2013 | D. Honegger, L. Meier, P. Tanskanen, M. Pollefeys: An Open Source and Open Hardware Embedded Metric Optical Flow CMOS Camera for Indoor and Outdoor Applications, Proc. IEEE ICRA, 2013 | 実在確認済み（ETH著者ページ）。**ページ番号は IEEE Xplore で要確認** |
| mcguire2017 | K. McGuire, G. de Croon, C. De Wagter, K. Tuyls, H. Kappen: Efficient Optical Flow and Stereo Vision for Velocity Estimation and Obstacle Avoidance on an Autonomous Pocket Drone, IEEE Robotics and Automation Letters, Vol.2, No.2, pp.1070–1076, 2017. DOI: 10.1109/LRA.2017.2658940 | 実在確認済み |
| flowdeck | Bitcraze AB: Flow deck v2 (製品Web) | Flow Deck 単体の査読論文は存在しない→製品として引用するのが実態に即す |
| kendoul2009 | F. Kendoul, I. Fantoni, K. Nonami: Optic Flow-Based Vision System for Autonomous 3D Localization and Control of Small Aerial Vehicles, Robotics and Autonomous Systems, Vol.57, No.6–7, pp.591–602, 2009. DOI: 10.1016/j.robot.2009.02.001 | **全文確認済み(2026-08-01)**。650gクアッドロータ、光流由来の速度・位置を機上制御器(50Hz)にフィードバックし自動離陸〜自動着陸の完全自律飛行を実証。千葉大・野波研グループ関与(オートパイロットは千葉大で製作と本文に明記、実験地は要注意)。1章[4]「国内グループによる飛行制御への適用」の根拠 |
| grabe2012 | V. Grabe, H. H. Bülthoff, P. Robuffo Giordano: On-board Velocity Estimation and Closed-loop Control of a Quadrotor UAV based on Optical Flow, Proc. IEEE ICRA, pp.491–497, 2012 | 全文確認済み。閉ループ速度制御実飛行(制御演算は地上局)。速度誤差0.039–0.084 m/s。未引用・4章以降の候補 |
| herisse2012 | B. Hérissé, T. Hamel, R. Mahony, F.-X. Russotto: Landing a VTOL Unmanned Aerial Vehicle on a Moving Platform Using Optical Flow, IEEE Trans. Robotics, Vol.28, No.1, pp.77–89, 2012 | 全文確認済み。光流PIフィードバックで移動台への自動着陸実飛行。未引用・候補 |
| bristeau2011 | P.-J. Bristeau, F. Callou, D. Vissière, N. Petit: The Navigation and Control Technology Inside the AR.Drone Micro UAV, Proc. 18th IFAC World Congress, 2011 | **アブスト+二次文献確認のみ(本文未取得)**。市販機の下向きカメラ速度推定が制御ループ内。「市販機・プラットフォーム文書化論文」の前例として1章二本柱化の際の引用候補。**引用前に本文入手を推奨** |
| zufferey2005 | J.-C. Zufferey, D. Floreano: Toward 30-gram Autonomous Indoor Aircraft: Vision-based Obstacle Avoidance and Altitude Control, Proc. IEEE ICRA, pp.2594–2599, 2005 | アブスト確認のみ。30g・光流閉ループだが**固定翼**。質量最近接の参考 |
| （取りやめ）ohtaki2014 | 大滝・岩倉・野波: オプティカルフローセンサを用いたUAVの飛行制御, ROBOMECH2014, 2A2-C02. DOI: 10.1299/jsmermd.2014._2a2-c02_1 | 全文確認の結果**閉ループ未実装(速度推定のVICON検証のみ)・機体約2kg級**のため1章引用を取りやめ(2026-08-01)。kendoul2009に差し替え |

**国内文献に関する注意（2026-08-01調査）**: 日本単独グループの「フロー閉ループ+実飛行」査読文献は未発見（熊本大2021系はシミュレーションのみの疑い）。関連研究で国内実証に言及する場合は「国内グループによる」(kendoul2009)の表現に留める。調査時取得のPDF一次資料はセッションのscratchpad配下に保存（grabe2012.pdf等）。

## Crazyflie 系文献（2026-08-02 徹底調査・確認レベル付き）

| ラベル | 書誌 | 確認レベル・内容 |
|--------|------|-----------------|
| forster2015 | J. Förster: System Identification of the Crazyflie 2.0 Nano Quadrocopter, Bachelor Thesis, ETH Zurich, 2015. DOI: 10.3929/ethz-b-000214143 | **全文読了（147頁）**。質量28.0g・慣性行列・推力/トルク写像・モータ離散伝達関数・抗力3モデルを単一個体で同定。パラメータ開示論文の模範。4基間個体差・フロー・サグ・保持精度の言及なし |
| giernacki2017 | W. Giernacki et al.: Crazyflie 2.0 quadrotor as a platform for research and education in robotics and control engineering, Proc. MMAR 2017, pp.37–42. DOI: 10.1109/MMAR.2017.8046794 | **全文読了**。諸元・既定PIDゲイン表・**電池サグ補償式(5)を明示**。教育プラットフォーム論文の代表。保持精度の定量値なし |
| greiff2017 | M. Greiff: Modelling and Control of the Crazyflie Quadrotor for Aggressive and Autonomous Flight by Optical Flow Driven State Estimation, MSc Thesis, Lund Univ., TFRT-6026, 2017 | **全文読了**。設計手順の体系的記述（モデル→制御→スカラー更新EKF→実機）。PWM-推力比の電池依存を明記。フロー静止ドリフトの理論・実験。高度推定std≈1.6cm等 |
| eschmann2024 | J. Eschmann, D. Albani, G. Loianno: Data-Driven System Identification of Quadrotors Subject to Motor Delays, arXiv:2404.07837 | 該当箇所読了。CF2.1のモータ時定数 T_m=0.072s（公式実測≈0.073s・Förster 0.065sと3者近接）。モータ個別推力曲線に言及 |
| mueller2017 | M. W. Mueller, M. Hehn, R. D'Andrea: Covariance Correction Step for Kalman Filtering with an Attitude, J. Guidance, Control, and Dynamics, Vol.40, No.9, pp.2301–2306, 2017 | **アブストのみ（本文ペイウォール）**。Crazyflie公式EKFの理論基盤。引用前に本文入手推奨 |
| crazysim2024 | C. Llanes et al.: CrazySim: A Software-in-the-Loop Simulator for the Crazyflie Nano Quadrotor, Proc. IEEE ICRA 2024 | 本文未確認（GitHub README・公式ブログ確認）。**「SIL用改造ファームであり実機書込禁止」とREADME明記**＝Code Identity SILSではない。SILS章の差別化の根拠 |
| — | Bitcraze 公式ブログ・文書群（サグ補償2025/10、フロー床面条件、EKF supervisor 等） | 直接確認済み。困難B.1-B.5の既報の一次情報源。URL引用の形式は要検討 |

**帰結**: 小型機の困難（モータ個体差・電池サグ・フロー床面依存・遅れ・EKF工夫）は全て Crazyflie 系で既報 → 論文では「発見」と書かず対応付けで引用。Crazyflie に**実機同一ソースの決定論的SILSは無い**（公式discussion #995で非サポート明言）。**xy閉ループ位置保持精度の公表値も見当たらない**（±6〜7cmの報告自体に資料価値）。
| — | StampFly を扱った学術文献 | **未発見**（2026-08-01時点）→「著者の知る限り先行学術報告は見当たらない」と書ける |

## 未検証・保留

- 「時間スケール分離」（4章で使用予定）— 未検証。使用前に要検証
- 「誤差状態カルマンフィルタ（ESKF）」の和訳慣用（3章で使用予定）— 未検証。使用前に要検証
- 「外乱オブザーバ」「アンチワインドアップ」等の2章以降の用語 — 使用前に要検証
