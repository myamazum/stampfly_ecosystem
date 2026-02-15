#!/usr/bin/env python3
"""X API v2 で投稿するスクリプト（画像添付対応）"""

import argparse
import os
import sys

try:
    import requests
    from requests_oauthlib import OAuth1
except ImportError:
    print("エラー: 必要なパッケージがインストールされていません")
    print("以下のコマンドでインストールしてください:")
    print("  pip install requests requests-oauthlib")
    sys.exit(1)


REQUIRED_ENV_VARS = [
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
]

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def check_env_vars() -> list[str]:
    """必要な環境変数が設定されているか確認"""
    return [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]


def get_auth() -> OAuth1:
    """OAuth1 認証オブジェクトを生成"""
    return OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def validate_media_file(filepath: str) -> str | None:
    """画像ファイルのバリデーション。エラーメッセージを返す（問題なければ None）"""
    if not os.path.exists(filepath):
        return f"ファイルが見つかりません: {filepath}"

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"非対応の形式です（{ext}）。対応形式: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    size = os.path.getsize(filepath)
    if size > MAX_FILE_SIZE:
        size_mb = size / (1024 * 1024)
        return f"ファイルサイズが大きすぎます（{size_mb:.1f}MB）。上限: 5MB"

    return None


def upload_media(filepath: str, auth: OAuth1) -> str:
    """画像をアップロードし media_id_string を返す"""
    # Upload endpoint (v1.1)
    # メディアアップロードは v1.1 API を使用
    url = "https://upload.twitter.com/1.1/media/upload.json"

    with open(filepath, "rb") as f:
        files = {"media": f}
        response = requests.post(url, auth=auth, files=files)

    if response.status_code in (200, 201, 202):
        return response.json()["media_id_string"]
    else:
        raise RuntimeError(
            f"メディアアップロード失敗 ({response.status_code}): {response.text}"
        )


def post_tweet(text: str, media_ids: list[str] | None = None) -> dict:
    """X に投稿する"""
    auth = get_auth()

    payload: dict = {"text": text}
    if media_ids:
        payload["media"] = {"media_ids": media_ids}

    response = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json=payload,
    )

    if response.status_code == 201:
        return {"success": True, "data": response.json()}
    else:
        return {"success": False, "error": response.text, "status_code": response.status_code}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="X (Twitter) に投稿する")
    parser.add_argument("message", help="投稿するメッセージ")
    parser.add_argument(
        "--media",
        help="添付する画像パス（カンマ区切りで最大4枚）",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="投稿せずにプレビューのみ表示",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    message = args.message

    # 環境変数チェック（dry-run 以外）
    if not args.dry_run:
        missing = check_env_vars()
        if missing:
            print("エラー: 以下の環境変数が未設定です:")
            for var in missing:
                print(f"  - {var}")
            print()
            print("~/.zshrc に以下を追加してください:")
            print('  export X_API_KEY="your-api-key"')
            print('  export X_API_SECRET="your-api-secret"')
            print('  export X_ACCESS_TOKEN="your-access-token"')
            print('  export X_ACCESS_TOKEN_SECRET="your-access-token-secret"')
            sys.exit(1)

    if len(message) > 280:
        print(f"警告: {len(message)}文字（280文字超過）")

    # メディアファイルの処理
    media_paths: list[str] = []
    if args.media:
        media_paths = [p.strip() for p in args.media.split(",") if p.strip()]
        if len(media_paths) > 4:
            print("エラー: 画像は最大4枚までです")
            sys.exit(1)
        for path in media_paths:
            error = validate_media_file(path)
            if error:
                print(f"エラー: {error}")
                sys.exit(1)

    # dry-run モード
    if args.dry_run:
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📝 投稿プレビュー ({len(message)}文字):")
        print()
        print(message)
        if media_paths:
            print()
            print(f"📎 添付画像 ({len(media_paths)}枚):")
            for i, path in enumerate(media_paths, 1):
                size_kb = os.path.getsize(path) / 1024
                print(f"  {i}. {path} ({size_kb:.0f}KB)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return

    # メディアアップロード
    media_ids: list[str] = []
    if media_paths:
        auth = get_auth()
        for path in media_paths:
            print(f"📤 アップロード中: {os.path.basename(path)}...")
            try:
                media_id = upload_media(path, auth)
                media_ids.append(media_id)
                print(f"  ✓ 完了 (media_id: {media_id})")
            except RuntimeError as e:
                print(f"  ✗ {e}")
                sys.exit(1)

    # 投稿
    result = post_tweet(message, media_ids if media_ids else None)

    if result["success"]:
        tweet_id = result["data"]["data"]["id"]
        print("✓ 投稿成功!")
        print(f"  https://x.com/i/status/{tweet_id}")
    else:
        print(f"✗ 投稿失敗: {result.get('status_code')} {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
