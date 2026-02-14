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


def extract_section(body: str, section_name: str) -> list[str]:
    """コミット本文から特定セクションの項目を抽出"""
    if section_name not in body:
        return []

    # セクション開始位置を探す
    start_idx = body.find(section_name)
    if start_idx == -1:
        return []

    # セクション内容を取得（次のセクションまたは本文終了まで）
    section_start = start_idx + len(section_name)
    rest_of_body = body[section_start:]

    # 次のセクション（大文字で始まる行）を探す
    lines = rest_of_body.split('\n')
    section_lines = []
    for line in lines:
        # 空行はスキップ
        if not line.strip():
            continue
        # 次のセクション（大文字で始まる、または "Next steps:" など）なら終了
        if line.strip() and not line.startswith((' ', '-', '  -')) and ':' in line:
            if line.split(':')[0].strip() not in section_lines:
                break
        # 箇条書き項目を収集
        if line.strip().startswith('-'):
            section_lines.append(line.strip()[2:])  # "- " を削除

    return section_lines


def generate_post(commits: list[dict], user_message: str = "") -> str:
    """投稿文を生成"""
    if not commits:
        return ""

    # 冒頭（コミット数明示）
    intro = user_message + "\n\n" if user_message else ""

    # 全コミットから背景説明を集約（日本語の段落を優先）
    background = []
    for commit in commits[:2]:  # 最初の2件から背景を抽出
        body = commit['body'].strip()
        first_para = body.split('\n\n')[0] if body else ""
        # 日本語を含む段落を優先
        if first_para and any(ord(c) > 127 for c in first_para):
            background.append(first_para)

    if background:
        intro += background[0] + "\n\n"
    else:
        intro += f"StampFlyドローンの開発を進めた（{len(commits)}件のコミット）。\n\n"

    # 実装内容（Changes セクションから抽出）
    all_changes = []
    for commit in commits:
        changes = extract_section(commit['body'], 'Changes:')
        all_changes.extend(changes[:3])  # 各コミットから最大3項目

    impl_text = "実装内容：\n"
    for change in all_changes[:5]:  # 最大5項目
        impl_text += f"・{change}\n"
    impl_text += "\n"

    # 詳細セクション（複数のセクションから生成）
    details = []
    for commit in commits[:3]:  # 最大3件の詳細
        body = commit['body'].strip()
        subject = commit['subject'].split(':', 1)[1].strip() if ':' in commit['subject'] else commit['subject']

        # Architecture セクション（アーキテクチャ説明）
        arch_items = extract_section(body, 'Architecture:')
        if arch_items and len(arch_items) > 0:
            arch_desc = "。".join(arch_items[:3])
            details.append(f"◆{subject}アーキテクチャ: {arch_desc}")

        # Commands セクション（コマンド一覧）
        cmd_items = extract_section(body, 'Commands:')
        if cmd_items and len(cmd_items) > 0:
            cmd_desc = "、".join(cmd_items[:4])
            details.append(f"◆コマンド: {cmd_desc}")

        # Implementation セクション（詳細に展開）
        impl_items = extract_section(body, 'Implementation:')
        if impl_items and len(impl_items) > 0:
            impl_desc = "。".join(impl_items[:4])
            details.append(f"◆実装: {impl_desc}")

        # Technical details / Implementation notes セクション
        tech_items = extract_section(body, 'Technical details:')
        if not tech_items:
            tech_items = extract_section(body, 'Implementation notes:')
        if tech_items and len(tech_items) > 0:
            tech_desc = "。".join(tech_items[:3])
            details.append(f"◆技術詳細: {tech_desc}")

        # User Benefits セクション
        benefit_items = extract_section(body, 'User Benefits:')
        if benefit_items and len(benefit_items) > 0:
            benefit_desc = "。".join(benefit_items[:3])
            details.append(f"◆効果: {benefit_desc}")

        # Behavior セクション（新機能の場合）
        behavior_items = extract_section(body, 'Behavior:')
        if behavior_items and len(behavior_items) > 0:
            behavior_desc = "。".join(behavior_items[:3])
            details.append(f"◆動作: {behavior_desc}")

    # 詳細が多い場合は調整（最大5セクション）
    if len(details) > 5:
        details = details[:5]

    detail_text = "\n\n".join(details) + "\n\n" if details else ""

    # 締め（成果のインパクト）- コミット数に応じて変化
    if len(commits) >= 3:
        closing = f"これらの機能追加により、StampFly開発環境が大幅に強化され、実機テストから進捗共有まで一貫した開発フローが確立。開発効率が大きく向上した\n\n"
    else:
        closing = "StampFly開発環境が強化され、開発効率が向上\n\n"

    # ハッシュタグ（コミット内容に応じて調整）
    tags = ["#StampFly"]
    # scope に応じてタグを追加
    scopes = [c['subject'].split('(')[1].split(')')[0] if '(' in c['subject'] else "" for c in commits]
    if any('cli' in s or 'flight' in s or 'workflow' in s for s in scopes):
        tags.append("#ドローン開発")
    if any('control' in s for s in scopes):
        tags.append("#制御工学")
    tags.append("#ESP32")
    hashtags = " ".join(tags[:3])  # 最大3個

    post = intro + impl_text + detail_text + closing + hashtags

    # 文字数制限チェック（段階的に調整、目標800-900文字）
    # X (Twitter) は現在数千文字まで可能だが、読みやすさのため1000文字程度に抑える
    if len(post) > 1000:
        # Step 1: 詳細セクションを4つに削減
        if len(details) > 4:
            detail_text = "\n\n".join(details[:4]) + "\n\n"
            post = intro + impl_text + detail_text + closing + hashtags

    if len(post) > 1000:
        # Step 2: 詳細セクションを3つに削減
        if len(details) > 3:
            detail_text = "\n\n".join(details[:3]) + "\n\n"
            post = intro + impl_text + detail_text + closing + hashtags

    if len(post) > 1000:
        # Step 3: 実装内容を3項目に削減
        impl_text = "実装内容：\n"
        for change in all_changes[:3]:
            impl_text += f"・{change}\n"
        impl_text += "\n"
        post = intro + impl_text + detail_text + closing + hashtags

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
