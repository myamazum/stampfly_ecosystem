# sf eskf

ESKF（Error-State Kalman Filter）シミュレーション・パラメータチューニングコマンド。

## 構文

```bash
sf eskf <subcommand> [options]
```

### サブコマンド

| サブコマンド | 説明 |
|-------------|------|
| `replay` | センサログから ESKF をリプレイ（CSV 入力 -> 状態出力） |
| `compare` | 推定値と参照値の比較（誤差メトリクス） |
| `params` | パラメータ管理（表示・変換・差分） |
| `tune` | パラメータ最適化（SA, GD, Grid） |
| `plot` | 可視化（matplotlib） |

## 使用例

```bash
sf eskf replay flight_log.csv
sf eskf params show
sf eskf tune --method sa
```

> 詳細なドキュメントは今後追加予定です。
