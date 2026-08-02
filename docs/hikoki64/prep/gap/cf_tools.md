# Bitcraze Crazyflie エコシステム到達点 調査報告

調査日: 2026-08-02（WebFetch/WebSearchによる公式情報源の直接確認に基づく）
方針: 確認できた事実のみを出典URL付きで記載。推測・記憶からの補完はしない。確認できなかった項目は「未確認」と明記。

---

## 1. cfclient（GUI）の機能範囲

出典: https://www.bitcraze.io/documentation/repository/crazyflie-clients-python/master/ 、
https://www.bitcraze.io/documentation/repository/crazyflie-clients-python/master/userguides/userguide_client/

- 公式説明: 「The Crazyflie PC client enables flashing and controlling the Crazyflie. It implements the user interface and high-level control (for example gamepad handling)」
- ユーザーガイドに記載されているタブ/機能:
  - **Flightcontrol Tab** — 手動操縦・ジョイスティック/ゲームパッド制御
  - **Console Tab** — ログ出力表示
  - **LED Ring tab** — LEDリングデッキの設定
  - **Color LED tab** — カラーLEDデッキ制御
  - **Log Blocks Tab** / **Log TOC Tab** / **Log Client Tab** — ロギング設定・変数一覧・管理
  - **Parameter Tab** — オンボードパラメータの設定
  - **Plotter Tab** — フライトデータのプロット・保存
  - **Loco Positioning Tab** — Loco Positioning System（UWB測位）の設定・可視化
  - **Lighthouse Positioning Tab** — Lighthouse測位システムの設定
  - **Tuning Tab** — チューニング機能
  - **CRTP Sniffer Tab** — CRTPプロトコルの解析
- その他確認できた機能:
  - ファームウェアアップグレード（機体本体だけでなくデッキファームウェアも対象）
  - Recovery firmware flashing（リカバリ書き込み手順が別ページで用意されている）
  - デバイスマッピング設定（ゲームパッド/ジョイスティックのカスタムマッピング）
  - マルチコントローラーモード（教師モード RP / RPYT の記載あり）
  - ラジオ設定（チャネル、帯域幅、アドレス変更）
  - ZMQバックエンド接続（外部プロセスからパラメータ制御・LED制御・入力デバイス機能にアクセス可能）
- **未確認**: 多言語（ローカライゼーション）対応の有無。拡張・プラグイン機構（extension/plugin API）の存在は検索では明確な一次情報が見つからず未確認。
- GitHub: https://github.com/bitcraze/crazyflie-clients-python — スター344、最終push 2026-07-30（GitHub API確認）

## 2. cflib（Python API）の機能範囲・スワームAPI

出典: https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/ 、
https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/user-guides/sbs_connect_log_param/ 、
https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/user-guides/sbs_swarm_interface/ 、
https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/user-guides/sbs_motion_commander/ 、
https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/api/cflib/crazyflie/high_level_commander/

### 主要クラス（確認済み）
- `cflib.crtp` — 接続可能なCrazyflieのスキャン
- `Crazyflie` — 接続・データ送受信の中心クラス
- `SyncCrazyflie` — 非同期APIを同期的なブロッキング関数に変換するラッパー
- `LogConfig` / `SyncLogger` — ロギング設定・同期アクセス
- `cf.param` — パラメータ読み書き（`add_update_callback`, `set_value` 等）
- `MotionCommander` — 離陸時に自動離陸、コンテキスト終了時に自動着陸。`forward()`/`back()`/`up()`/`turn_left()` 等のブロッキング移動、`start_forward()` 等の非ブロッキング移動、`start_linear_motion(x,y,z)` によるボディ座標系速度指令
- `HighLevelCommander` — 機体オンボード側のプランナに `takeoff`/`land`/`goTo` を非同期コマンドとして送信。`uploadTrajectory()` によるメモリサブシステム経由の区分多項式軌道（7次多項式）アップロードに対応。`goTo` の高頻度・短時間呼び出しは不安定化しうるため `cmdPosition()` 推奨との注記あり

### スワームAPI（`cflib.crazyflie.swarm.Swarm`）
- `parallel_safe()` — 全機体で同一処理を並列実行（内部でスレッド管理）
- `sequential()` — 機体ごとに順番に処理
- `parallel()` — 並列実行（例外時の挙動が`parallel_safe`と異なる）
- 各Crazyflieは`SyncCrazyflie`インスタンスとして扱われ、`args_dict`パラメータで機体URIごとに異なる引数を指定可能
- チュートリアル例: `swarm.reset_estimators()` による位置推定リセット後、4機が1m×1mの正方形を同時飛行する同期デモ
- リーダー・フォロワー構成への言及はチュートリアル内には確認できず（全機体が独立して同一/個別シーケンスを実行する構成）
- 出典: https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/api/cflib/crazyflie/swarm/ 、 https://github.com/bitcraze/crazyflie-lib-python/blob/master/cflib/crazyflie/swarm.py

### その他
- Python Crazyradio Library（`cflib.crtp.radiodriver`系）の存在を確認
- CRTP通信デバッグ、EEPROM操作、UART通信、MATLAB連携に関するドキュメントページの存在を確認（詳細な機能内容までは未確認）
- GitHub: https://github.com/bitcraze/crazyflie-lib-python — スター341、最終push 2026-07-27（GitHub API確認）

## 3. Crazyswarm2 / ROS 2 統合の状態

出典: https://github.com/IMRCLab/crazyswarm2 、 https://imrclab.github.io/crazyswarm2/ 、
https://imrclab.github.io/crazyswarm2/installation.html

- 対応ハードウェア: 「aerial robots that use flight computers from Bitcraze AB, including the Crazyflie 2.1(+), Crazyflie 2.1 Brushless, Flapper Nimble+, and custom drones built using Crazyflie Bolt」
- 対応OS/ROS 2ディストリビューション（インストールページ記載の組み合わせ）:
  | Ubuntu | Python | ROS 2 |
  |---|---|---|
  | 22.04 | 3.10 | Humble |
  | 24.04 | 3.12 | Jazzy |
- 依存パッケージ: `libboost-program-options-dev`, `libusb-1.0-0-dev`, `rowan`（Python）, `motion-capture-tracking`（ROS 2パッケージ）。CFlibバックエンド使用時は追加で `cflib`, `transforms3d`, `tf-transformations` が必要
- チュートリアル: 「ROS 2 Tutorials」セクション、および「Aerial Swarm Tools and Applications Tutorial/Workshop」への言及あり（内容詳細は未確認）
- 開発体制（GitHub API確認、2026-08-02時点）:
  - スター 245、フォーク 126、ウォッチャー 7、ライセンス MIT
  - 最終push: 2026-07-27（活発に更新継続中）
  - オープンissue数: 61
- **未確認**: crazyflie_server等のノード構成詳細、モーションキャプチャ連携の具体的対応製品リスト、シミュレーション統合（CrazySim等）との連携の技術詳細はトップページからは確認できず、個別ページの参照が必要

## 4. シミュレータの選択肢

出典: https://www.bitcraze.io/documentation/tutorials/getting-started-with-simulation/ 、
https://www.bitcraze.io/development/external-projects/ 、
https://www.bitcraze.io/2024/04/crazysim-a-software-in-the-loop-simulator-for-the-crazyflie/

Bitcraze公式の「external projects」ページに一覧化されているシミュレータ（**Bitcraze公式が直接開発しているのはWebotsサンプルのみで、他はすべて外部/非公式プロジェクトとして掲載**）:

| プロジェクト | 開発元 | 位置づけ（公式記載） | リンク |
|---|---|---|---|
| Webots | Cyberbotics | 公式ドキュメントの「Getting Started」で紹介される唯一のシミュレータ。ただし公式ページ自身が「not realistic, feature-rich, or actively maintained」と明記。キーボード操作・壁沿い自律飛行の例あり | https://cyberbotics.com/doc/guide/crazyflie |
| CrazySim | Georgia Tech FACTS Lab（Christian Llanes氏ら） | ROS 1不要、Gazebo Sim（Gazebo Classicから刷新）を物理エンジンに使用するSITL。CFLib経由でCrazyswarm2やcfclientに接続可能。ICRA 2024論文の付随コード。Gazebo/MuJoCoの2つの物理バックエンド対応 | https://github.com/gtfactslab/CrazySim（GitHub API: スター147、最終push 2026-04-03、非アーカイブ） |
| CrazyS | Università del Sannio（gsilano氏） | ROS 1（Kinetic/Melodic/Noetic、Indigoは非推奨）向けのGazebo拡張。RotorSの拡張版。**ROS 2非対応** | https://github.com/gsilano/CrazyS（GitHub API: スター178、最終push 2022-08-11、非アーカイブだが3年以上更新なし） |
| gym-pybullet-drones | University of Toronto DSL / Vector Institute / Cambridge Prorok Lab | PyBullet基盤のGymnasium環境。Stable-Baselines3 2.0対応、crazyflie-firmware SITL連携あり | https://github.com/utiasDSL/gym-pybullet-drones（スター2,100、2026年GitHub Maintainer Spotlightに選出とWebFetchで報告されたが**この選出情報は一次情報未確認**） |
| Crazyflow | University of Toronto DSL | JAX + MuJoCoの高性能シミュレーションフレームワーク | https://github.com/utiasDSL/crazyflow |
| Sim_CF2 | CrazyflieTHI | 旧Sim_CFのROS 2アップグレード版 | https://github.com/CrazyflieTHI/sim_cf2 |
| Sim_cf | wuwushrek | Gazebo+ROS連携のHITL/SITL | https://github.com/wuwushrek/sim_cf |
| LambdaFlight | Simon D. Levy | Haskell向け最小限SITL（Webots対応） | https://github.com/simondlevy/LambdaFlight |
| MuJoCo公式モデル | DeepMind | MuJoCoモデル集にCrazyflie 2.xモデルを収録 | https://mujoco.readthedocs.io/en/3.3.3/models.html#drones |
| NVIDIA Isaac Sim | NVIDIA | Isaac SimのリファレンスアセットにCrazyflieモデルあり | （Bitcrazeページ記載のリンク） |
| Rviz Simulator | Malintha | RvizベースのCrazyflie 2.0シミュレーション | https://github.com/malintha/multi_uav_simulator |

補足（Bitcrazeブログより）:
- 「The State of Crazyflie Simulations」(2021-12) と「Development plans for Crazyflie Simulation」(2023-10) というシミュレーション戦略に関する記事の存在を確認（内容詳細は未確認、URLのみ確認: https://www.bitcraze.io/2021/12/simulation-possibilities/ 、 https://www.bitcraze.io/2023/10/development-plans-for-crazyflie-simulation/ ）
- CrazySim公式ブログ記事は「Gazebo Sim（新版）」「CFLib接続」「Crazyswarm2連携」を明記。ただし公式ブログ記事内のGitHubリンクは `github.com/gtfactslab/Llanes_ICRA2024` を指しており、現行の開発リポジトリは `github.com/gtfactslab/CrazySim`（README上で公式と明記）。**この2リポジトリの関係（前者が論文コード、後者が現行版）は推測含みのため注意**

## 5. 教育利用

出典: https://www.bitcraze.io/2025/07/teaching-robotics-with-the-crazyflie/ 、
https://www.bitcraze.io/2022/01/introduction-to-robotics-at-princeton/ （検索結果スニペットで確認、本文未フェッチ）、
https://www.bitcraze.io/2024/07/why-droneblocks-chose-the-bitcraze-crazyflie-as-their-go-to-stem-drone/ （検索結果スニペットで確認、本文未フェッチ）

- Bitcraze公式ブログ「Teaching Robotics with the Crazyflie」(2025-07) で確認された大学講義の実例:
  - **プリンストン大学** — 「Introduction to Robotics」（機械・航空工学部/MAE 345・ECE 345・COS 346、学部3-4年生対象＋大学院トラックあり。2021年秋学期で学部生約70名・院生約10名が履修、との記載を検索結果スニペットで確認）
  - **カリフォルニア大学バークレー校** — 「Introduction to Control of Unmanned Aerial Vehicles」
  - **チャルマース工科大学（スウェーデン）** — 「Embedded control systems」
  - 記事はCrazyflieで教えられる分野として「基本的なドローン原理」「制御システム」「ローカライゼーション」「自律航行」「スワームロボティクス」を列挙
- **DroneBlocks社との教育パートナーシップ**（K-12/STEM向け）: 「DroneBlocks Autonomous Drones Level II kit」がCrazyflieを採用。Bitcraze公式ブログ (2024-07) で「discontinued DJI Tello Droneの後継として採用」との記載を検索結果スニペットで確認
- 検索結果スニペットで「University of Washington」の「Bio-inspired Robotics」講義（Prof. Sawyer Fuller）でのCrazyflie使用、「University of Twente」のUAV関連コースポータルへの言及も見つかったが、**いずれも一次ページの直接フェッチはできておらず未確認**（`https://www.bitcraze.io/portals/education/` は404で本文確認不能）
- **未確認**: 公式の体系的な「教育用チュートリアル教材一式」（大学向けシラバス・課題セット等）がBitcraze自身から配布されているかどうかは、教育ポータルページ自体にアクセスできなかったため確認できていない。ドキュメントサイトのStep-by-Stepガイド群（cflib/cfclient双方に存在）は教育目的にも使われうるが、大学向けカリキュラムとして公式提供されているかは未確認

## 6. コミュニティ体制

### フォーラム（旧）
出典: https://forum.bitcraze.io/ 、 https://forum.bitcraze.io/index.php

- 旧フォーラム（phpBB形式）は**読み取り専用**。バナー文言: "This forum is read-only, please start new threads on the Bitcraze discussions page instead"
- アーカイブ告知: "This forum was archived on March 30, 2026"
- 旧フォーラムのカテゴリ構成（確認時点）: General、Crazyflie Nano Quadcopter、Crazyradio、Positioning systems and autonomous flight、AI-deck、およびサブフォーラム Bitcraze discussions(367トピック)、Quadcopters discussions(145)、Crazyflie General discussions(552)、Developer Discussions(1,393)、Support(988)、Loco Positioning System(351)、Lighthouse positioning system(97)
- 累計統計: 投稿23,053、トピック4,515、メンバー3,827（アクティブ活動は2022年6月3日ごろで停止）

### 現行コミュニティ（GitHub Discussions）
出典: https://www.bitcraze.io/2022/05/community-moves-to-github-discussions/ 、
https://github.com/orgs/bitcraze/discussions

- 2022年5月のブログ記事で、旧フォーラムから**GitHub Discussionsへの全面移行**を告知。移行時期は「2022年6月6日の週から旧フォーラムは新規スレッド作成・登録をロック」
- 移行理由（ブログ記載）: 旧フォーラムの機能が停滞、開発チームがフォーラムとGitHub issueを往復する二重管理の負担、コミュニティ活動の減少
- Discordチャンネルは2020年に開設されたが「活動が本格化しなかった」上「ハッキング被害後に招待リンクを削除」し、最終的にGitHub Discussionsへ統一（`discussions.bitcraze.io` は現在 `github.com/orgs/bitcraze/discussions` へ301リダイレクト、確認済み）
- GitHub Discussionsのカテゴリ構成: Announcements、General、Ideas、Polls、Q&A、Show and tell
- コアメンテナ（ataffanel, gemenerik, ArisMorgens等）がQ&Aに応答している状況を確認。位置測位系（Loco/Lighthouse/UWB）、AIデッキ統合、トラブルシューティング等の活発なスレッドあり

### 開発者ミーティング
出典: https://www.bitcraze.io/documentation/meetings/ 、
https://github.com/orgs/bitcraze/discussions/540

- 「毎月第1水曜日」に開催（"Every first Wednesday of the month we have the Bitcraze Developer meeting"）
- 告知はdiscussion platformとEventsページで実施
- 議事はGitHub Discussionsに投稿される例を確認（例: 2023年2月22日開催回でCrazyradio 2.0、新無線プロトコル、デッキ開発インターフェース、Rust移行検討などが議題として記録されている discussion #540）
- **未確認**: 開催形式（オンライン/対面）、参加方法の詳細

### GitHub組織全体
出典: GitHub API直接確認（2026-08-02時点）

- 公開リポジトリ数: 77
- 組織フォロワー数: 669
- 主要リポジトリの活動状況（最終push日・スター数）:
  - crazyflie-firmware: スター1,520、最終push 2026-07-30、最新リリースタグ `2026.04`(公開日2026-04-13)
  - crazyflie-clients-python (cfclient): スター344、最終push 2026-07-30
  - crazyflie-lib-python (cflib): スター341、最終push 2026-07-27
  - crazyswarm2: スター245、最終push 2026-07-27
- 組織説明文: 「open platforms that enable people to explore the world of robotics」。スウェーデン・マルメ拠点、2011年創業（GitHub組織ページ記載）

## 7. 製品流通・価格帯

出典: https://store.bitcraze.io/collections/kits 、 https://store.bitcraze.io/collections/decks 、
https://store.bitcraze.io/collections/bundles

### 本体キット（単体、確認時点の表示価格。全て公式ストア直販、USD）
| 製品 | 価格 | 備考 |
|---|---|---|
| Crazyflie 2.1+ | $240.00 | |
| Crazyflie Bolt 1.1 | $205.00 | |
| Crazyflie 2.1 Brushless | $480.00 | 確認時点で「Temporarily out of stock」 |

### 主要デッキ（拡張ボード、確認できた全20製品）
| デッキ | 価格 |
|---|---|
| Active marker deck | $150.00 |
| AI-deck 1.1 | $240.00 |
| BigQuad deck | $9.00 |
| Breakout deck | $5.50 |
| Buzzer deck | $11.00 |
| Crazyflie Color LED Deck（Bottom/Top各種） | $23.00 |
| Female deck connector | $2.50 |
| Flow deck v2 | $55.00 |
| LED-ring deck | $23.00 |
| Lighthouse positioning deck | $95.00 |
| Loco positioning deck | $95.00 |
| Long Pins (15+4+6mm) | $2.00 |
| Motion capture marker deck | $6.50 |
| Multi-ranger deck | $95.00 |
| Prototyping deck | $5.50 |
| Qi 1.2 wireless charging deck | $38.00 |
| SD-card deck | $11.00 |
| Z-ranger deck | $18.00 |
| Z-ranger deck v2 | $23.00 |

### バンドル/キット構成（教育・スワーム向けを含む、確認時点の表示価格。一部セール価格併記）
| バンドル | 価格 |
|---|---|
| Getting started bundle - Crazyflie 2.1+ | $270.00（定価$285.00） |
| Getting started - Crazyflie 2.1 Brushless | $500.00（定価$523.00） |
| Happy hacker bundle - Crazyflie 2.1+ | $315.00（定価$331.50） |
| Happy hacker bundle - Crazyflie 2.1 Brushless | $540.00（定価$571.50） |
| STEM drone bundle - Crazyflie 2.1+ | $320.00（定価$338.00） |
| STEM bundle - Crazyflie 2.1 Brushless | $550.00（定価$578.00） |
| STEM ranging bundle | $410.00〜$640.00 |
| Infinite flight bundle - Crazyflie 2.1 Brushless | $1,075.00（定価$1,138.00） |
| Lighthouse explorer bundle | $810.00〜$1,050.00 |
| Loco explorer bundle | $1,720.00〜$1,950.00 |
| The AI bundle | $610.00〜$830.00 |
| Lighthouse swarm bundle - Crazyflie 2.1+ | $4,050.00 |
| Lighthouse swarm bundle - Crazyflie 2.1 Brushless | $6,100.00（定価$6,659.00） |
| Loco Swarm bundle | $5,000.00〜$7,200.00 |
| Flapper Nimble+ Starter Kit | $2,200.00 |

確認時点でバンドル製品は「全て在庫一時的に不足中」との表示あり。

---

## 未確認事項まとめ

- cfclientの多言語（ローカライゼーション）対応の有無
- cfclientの拡張・プラグイン機構（アプリレイヤーAPI）の存在・仕様
- Crazyswarm2のノード構成（crazyflie_server等）の詳細アーキテクチャ、モーションキャプチャ対応製品の具体リスト
- CrazySimの`gtfactslab/Llanes_ICRA2024`と`gtfactslab/CrazySim`の正確な関係（論文コードと現行開発版の対応関係は状況証拠のみ）
- gym-pybullet-drones の「2026年GitHub Maintainer Spotlight選出」情報（WebFetch要約に基づくが一次ソース未確認）
- Bitcraze公式の教育ポータルページ本文（`bitcraze.io/portals/education/`、`bitcraze.io/education/` とも404で直接確認できず）
- 開発者ミーティングの開催形式（オンライン/対面）・参加方法
- University of Washington「Bio-inspired Robotics」、University of Twente UAVコースポータルでのCrazyflie採用の一次情報（検索結果スニペットのみで本文未確認）
- cflibのCRTPデバッグ・EEPROM操作・UART通信・MATLAB連携機能の詳細内容（ページ存在は確認、内容は未確認）
