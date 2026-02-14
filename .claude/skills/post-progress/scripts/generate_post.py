#!/usr/bin/env python3
"""
コミット選択機能付き進捗投稿生成スクリプト

Usage:
    generate_post.py -n 5                    # 直近5件
    generate_post.py --select                # インタラクティブ選択
    generate_post.py --commits abc123,def456 # ハッシュ指定
    generate_post.py --range abc123..def456  # 範囲指定
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_commits_by_count(count: int) -> list[dict]:
    """直近N件のコミットを取得"""
    result = subprocess.run(
        ["git", "log", f"-{count}", "--format=%H|%s|%b"],
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_git_log(result.stdout)


def get_commits_by_days(days: int) -> list[dict]:
    """直近N日間のコミットを取得"""
    result = subprocess.run(
        ["git", "log", f"--since={days} days ago", "--format=%H|%s|%b"],
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_git_log(result.stdout)


def get_commits_by_hashes(hashes: list[str]) -> list[dict]:
    """指定されたハッシュのコミットを取得"""
    commits = []
    for hash in hashes:
        result = subprocess.run(
            ["git", "show", hash, "--format=%H|%s|%b", "--no-patch"],
            capture_output=True,
            text=True,
            check=True,
        )
        commits.extend(parse_git_log(result.stdout))
    return commits


def get_commits_by_range(range_spec: str) -> list[dict]:
    """範囲指定でコミットを取得"""
    result = subprocess.run(
        ["git", "log", range_spec, "--format=%H|%s|%b"],
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_git_log(result.stdout)


def parse_git_log(output: str) -> list[dict]:
    """git log の出力をパース"""
    commits = []
    current_commit = None

    for line in output.split('\n'):
        if '|' in line and len(line.split('|')[0]) == 40:  # コミットハッシュ行
            if current_commit:
                commits.append(current_commit)
            parts = line.split('|', 2)
            current_commit = {
                'hash': parts[0],
                'subject': parts[1],
                'body': parts[2] if len(parts) > 2 else ''
            }
        elif current_commit:
            # 本文の続き
            current_commit['body'] += '\n' + line

    if current_commit:
        commits.append(current_commit)

    return commits


def interactive_select() -> list[dict]:
    """インタラクティブにコミットを選択"""
    # 直近20件を表示
    result = subprocess.run(
        ["git", "log", "-20", "--oneline"],
        capture_output=True,
        text=True,
        check=True,
    )

    lines = result.stdout.strip().split('\n')

    print("=== コミット選択 ===")
    for i, line in enumerate(lines, 1):
        print(f"{i:2d}. {line}")
    print()
    print("選択したいコミット番号をカンマ区切りで入力 (例: 1,2,5):")

    selection = input("> ").strip()
    selected_indices = [int(x.strip()) - 1 for x in selection.split(',')]

    hashes = [lines[i].split()[0] for i in selected_indices]
    return get_commits_by_hashes(hashes)


def generate_post(commits: list[dict], user_message: str = "") -> str:
    """投稿文を生成"""
    if not commits:
        return ""

    # 冒頭
    intro = user_message + "\n\n" if user_message else ""
    intro += f"StampFlyドローンの開発を進めた（{len(commits)}件のコミット）。\n\n"

    # 実装内容を抽出
    implementations = []
    for commit in commits:
        subject = commit['subject']
        # type(scope): subject からパース
        if ':' in subject:
            type_scope, desc = subject.split(':', 1)
            implementations.append(f"・{desc.strip()}")

    impl_text = "実装内容：\n" + "\n".join(implementations[:5]) + "\n\n"

    # 詳細セクション（コミット本文から生成）
    details = []
    for commit in commits[:3]:  # 最大3件の詳細
        body = commit['body'].strip()
        if 'Changes:' in body:
            changes_section = body.split('Changes:')[1].split('\n\n')[0]
            details.append(f"◆{commit['subject'].split(':')[1].strip()}: {changes_section.strip()}")

    detail_text = "\n\n".join(details) + "\n\n" if details else ""

    # 締め
    closing = "開発環境と機能が充実し、実機テストの準備が整った\n\n"

    # ハッシュタグ
    hashtags = "#StampFly #ドローン開発 #Python"

    post = intro + impl_text + detail_text + closing + hashtags

    # 文字数制限チェック
    if len(post) > 950:
        # 詳細セクションを削減
        post = intro + impl_text + closing + hashtags

    return post


def main():
    parser = argparse.ArgumentParser(description='進捗投稿生成')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', type=int, help='直近N件のコミット')
    group.add_argument('--day', type=int, help='直近N日間のコミット')
    group.add_argument('--select', action='store_true', help='インタラクティブ選択')
    group.add_argument('--commits', help='コミットハッシュ（カンマ区切り）')
    group.add_argument('--range', help='範囲指定（例: abc123..def456）')

    parser.add_argument('-m', '--message', help='冒頭に追加するユーザーメッセージ')
    parser.add_argument('--dry-run', action='store_true', help='プレビューのみ')

    args = parser.parse_args()

    # コミット取得
    if args.n:
        commits = get_commits_by_count(args.n)
    elif args.day:
        commits = get_commits_by_days(args.day)
    elif args.select:
        commits = interactive_select()
    elif args.commits:
        hashes = [h.strip() for h in args.commits.split(',')]
        commits = get_commits_by_hashes(hashes)
    elif args.range:
        commits = get_commits_by_range(args.range)

    if not commits:
        print("エラー: コミットが見つかりません")
        sys.exit(1)

    # 投稿文生成
    post = generate_post(commits, args.message or "")

    # プレビュー表示
    print("=== 投稿プレビュー ===")
    print(post)
    print()
    print(f"文字数: {len(post)}文字")
    print()

    if args.dry_run:
        print("--dry-run モードのため、投稿しません")
        sys.exit(0)

    # 確認
    print("この内容で投稿しますか？ (y/N): ", end='')
    confirm = input().strip().lower()

    if confirm != 'y':
        print("キャンセルしました")
        sys.exit(0)

    # 投稿実行
    import os
    script_dir = Path(__file__).parent
    post_script = script_dir / "post_to_x.py"

    result = subprocess.run(
        [sys.executable, str(post_script), post],
        env=os.environ.copy(),
    )

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
