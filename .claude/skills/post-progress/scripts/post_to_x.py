#!/usr/bin/env python3
"""X API v2 で投稿するスクリプト"""

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


def check_env_vars() -> list[str]:
    """必要な環境変数が設定されているか確認"""
    return [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]


def post_tweet(text: str) -> dict:
    """X に投稿する"""
    auth = OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )

    response = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json={"text": text},
    )

    if response.status_code == 201:
        return {"success": True, "data": response.json()}
    else:
        return {"success": False, "error": response.text, "status_code": response.status_code}


def main():
    if len(sys.argv) < 2:
        print("Usage: post_to_x.py <message>")
        sys.exit(1)

    message = sys.argv[1]

    # 環境変数チェック
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

    result = post_tweet(message)

    if result["success"]:
        tweet_id = result["data"]["data"]["id"]
        print("✓ 投稿成功!")
        print(f"  https://x.com/i/status/{tweet_id}")
    else:
        print(f"✗ 投稿失敗: {result.get('status_code')} {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
