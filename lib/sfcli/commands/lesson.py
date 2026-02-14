"""
sf lesson - Workshop lesson management

Manages workshop lessons: list, switch, view solutions, build, flash.
ワークショップレッスンの管理: 一覧、切替、解答表示、ビルド、フラッシュ。

Subcommands:
    list      - List all available lessons
    switch    - Switch to a lesson (copy student.cpp to user_code.cpp)
    solution  - Show solution diff for a lesson
    build     - Build workshop firmware (= sf build workshop)
    flash     - Flash workshop firmware (= sf flash workshop -m)
"""

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from ..utils import console, paths

COMMAND_NAME = "lesson"
COMMAND_HELP = "Workshop lesson management"

# Lesson directory naming convention: lesson_NN_name
LESSONS_DIR = "lessons"
USER_CODE = "user_code.cpp"


def _get_lessons_dir() -> Path:
    """Get the lessons directory path"""
    return paths.workshop() / LESSONS_DIR


def _get_user_code_path() -> Path:
    """Get the user_code.cpp path"""
    return paths.workshop() / "main" / USER_CODE


def _discover_lessons() -> List[Tuple[int, str, Path]]:
    """Discover all available lessons.

    Returns list of (number, name, path) tuples sorted by number.
    """
    lessons_dir = _get_lessons_dir()
    if not lessons_dir.exists():
        return []

    lessons = []
    for d in sorted(lessons_dir.iterdir()):
        if not d.is_dir():
            continue
        # Parse lesson_NN_name format
        name = d.name
        if not name.startswith("lesson_"):
            continue
        parts = name.split("_", 2)
        if len(parts) < 3:
            continue
        try:
            num = int(parts[1])
        except ValueError:
            continue
        lesson_name = parts[2]
        lessons.append((num, lesson_name, d))

    return lessons


def _find_lesson(num: int) -> Optional[Path]:
    """Find lesson directory by number"""
    for n, _, path in _discover_lessons():
        if n == num:
            return path
    return None


def _get_lesson_title(lesson_dir: Path) -> str:
    """Get lesson title from README.md if available"""
    readme = lesson_dir / "README.md"
    if readme.exists():
        first_line = readme.read_text().split("\n")[0]
        # Strip markdown heading
        return first_line.lstrip("# ").strip()
    return lesson_dir.name


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register command with CLI"""
    parser = subparsers.add_parser(
        COMMAND_NAME,
        help=COMMAND_HELP,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    lesson_subparsers = parser.add_subparsers(
        dest="lesson_command",
        title="subcommands",
        metavar="<subcommand>",
    )

    # --- list ---
    list_parser = lesson_subparsers.add_parser(
        "list",
        help="List all available lessons",
        description="Show all workshop lessons with status.",
    )
    list_parser.set_defaults(func=run_list)

    # --- switch ---
    switch_parser = lesson_subparsers.add_parser(
        "switch",
        help="Switch to a lesson",
        description="Copy lesson student.cpp to user_code.cpp for building.",
    )
    switch_parser.add_argument(
        "number",
        type=int,
        help="Lesson number (e.g., 0, 1, 5)",
    )
    switch_parser.add_argument(
        "--solution",
        action="store_true",
        help="Use solution.cpp instead of student.cpp",
    )
    switch_parser.set_defaults(func=run_switch)

    # --- solution ---
    solution_parser = lesson_subparsers.add_parser(
        "solution",
        help="Show solution for a lesson",
        description="Display diff between student.cpp and solution.cpp.",
    )
    solution_parser.add_argument(
        "number",
        type=int,
        help="Lesson number (e.g., 5, 6)",
    )
    solution_parser.set_defaults(func=run_solution)

    # --- build ---
    build_parser = lesson_subparsers.add_parser(
        "build",
        help="Build workshop firmware",
        description="Build the workshop firmware (equivalent to 'sf build workshop').",
    )
    build_parser.add_argument(
        "-c", "--clean",
        action="store_true",
        help="Clean build (fullclean before build)",
    )
    build_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose build output",
    )
    build_parser.set_defaults(func=run_build)

    # --- flash ---
    flash_parser = lesson_subparsers.add_parser(
        "flash",
        help="Flash workshop firmware",
        description="Flash workshop firmware with monitor (equivalent to 'sf flash workshop -m').",
    )
    flash_parser.add_argument(
        "-p", "--port",
        default=None,
        help="Serial port (auto-detect if not specified)",
    )
    flash_parser.add_argument(
        "-b", "--baud",
        type=int,
        default=460800,
        help="Baud rate (default: 460800)",
    )
    flash_parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Don't start monitor after flashing",
    )
    flash_parser.set_defaults(func=run_flash)

    # Default: show help
    parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])


def run_list(args: argparse.Namespace) -> int:
    """List all available lessons"""
    lessons = _discover_lessons()

    if not lessons:
        console.error("No lessons found")
        console.print(f"  Expected at: {_get_lessons_dir()}")
        return 1

    # Check current lesson
    user_code_path = _get_user_code_path()
    current_content = ""
    if user_code_path.exists():
        current_content = user_code_path.read_text()

    console.header("Workshop Lessons")
    console.print()

    for num, name, path in lessons:
        # Check if files exist
        has_student = (path / "student.cpp").exists()
        has_solution = (path / "solution.cpp").exists()
        has_readme = (path / "README.md").exists()

        # Check if this is the current lesson
        is_current = False
        if has_student and current_content:
            student_content = (path / "student.cpp").read_text()
            if student_content == current_content:
                is_current = True
        if not is_current and has_solution and current_content:
            solution_content = (path / "solution.cpp").read_text()
            if solution_content == current_content:
                is_current = True

        # Format status indicators
        marker = " >> " if is_current else "    "
        title = _get_lesson_title(path)
        files = []
        if has_student:
            files.append("student")
        if has_solution:
            files.append("solution")
        if has_readme:
            files.append("readme")

        console.print(f"{marker}Lesson {num:02d}: {name}")
        if title != path.name:
            console.print(f"              {title}")
        console.print(f"              [{', '.join(files)}]")
        console.print()

    console.print(f"  Total: {len(lessons)} lessons")
    console.print(f"  Switch: sf lesson switch <N>")

    return 0


def run_switch(args: argparse.Namespace) -> int:
    """Switch to a lesson"""
    lesson_dir = _find_lesson(args.number)

    if lesson_dir is None:
        console.error(f"Lesson {args.number} not found")
        # Show available lessons
        lessons = _discover_lessons()
        if lessons:
            nums = [str(n) for n, _, _ in lessons]
            console.print(f"  Available: {', '.join(nums)}")
        return 1

    # Determine source file
    if args.solution:
        src = lesson_dir / "solution.cpp"
        label = "solution"
    else:
        src = lesson_dir / "student.cpp"
        label = "student"

    if not src.exists():
        console.error(f"{label}.cpp not found for Lesson {args.number}")
        return 1

    dst = _get_user_code_path()

    # Copy file
    shutil.copy2(src, dst)

    console.success(f"Switched to Lesson {args.number:02d} ({label})")
    console.print(f"  Source: {src}")
    console.print(f"  Target: {dst}")
    console.print()
    console.info("Next: sf lesson build && sf lesson flash")

    return 0


def run_solution(args: argparse.Namespace) -> int:
    """Show solution diff for a lesson"""
    lesson_dir = _find_lesson(args.number)

    if lesson_dir is None:
        console.error(f"Lesson {args.number} not found")
        return 1

    student = lesson_dir / "student.cpp"
    solution = lesson_dir / "solution.cpp"

    if not student.exists():
        console.error(f"student.cpp not found for Lesson {args.number}")
        return 1

    if not solution.exists():
        console.error(f"solution.cpp not found for Lesson {args.number}")
        return 1

    console.header(f"Lesson {args.number:02d} Solution Diff")
    console.print()

    # Use diff command
    result = subprocess.run(
        ["diff", "-u", "--color=auto", str(student), str(solution)],
        capture_output=False,
    )

    if result.returncode == 0:
        console.info("student.cpp and solution.cpp are identical")

    return 0


def run_build(args: argparse.Namespace) -> int:
    """Build workshop firmware"""
    from . import build as build_cmd

    build_args = argparse.Namespace(
        target="workshop",
        clean=args.clean,
        jobs=None,
        verbose=args.verbose,
    )
    return build_cmd.run(build_args)


def run_flash(args: argparse.Namespace) -> int:
    """Flash workshop firmware"""
    from . import flash as flash_cmd

    flash_args = argparse.Namespace(
        target="workshop",
        port=args.port,
        baud=args.baud,
        build=False,
        monitor=not args.no_monitor,
    )
    return flash_cmd.run(flash_args)
