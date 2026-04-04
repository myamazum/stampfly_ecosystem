# sf lesson

ワークショップレッスンの管理: 一覧、切替、解答表示、ビルド、フラッシュ。

## 構文

```bash
sf lesson <subcommand> [args]
```

### サブコマンド

| サブコマンド | 説明 |
|-------------|------|
| `list` | 利用可能なレッスン一覧を表示 |
| `switch <N>` | レッスンに切替（student.cpp を user_code.cpp にコピー） |
| `solution <N>` | レッスンの解答差分を表示 |
| `info <N>` | レッスンの詳細情報を表示 |
| `build` | ワークショップファームウェアをビルド |
| `flash` | ワークショップファームウェアを書き込み |

## 使用例

```bash
sf lesson list
sf lesson switch 3
sf lesson solution 3
sf lesson build
```

> 詳細なドキュメントは今後追加予定です。
