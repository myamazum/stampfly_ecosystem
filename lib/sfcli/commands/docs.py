"""
sf docs - Serve and build documentation site

MkDocs を使用してドキュメントサイトを提供・ビルドします。
"""

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path
from ..utils import console, paths

COMMAND_NAME = "docs"
COMMAND_HELP = "Serve and build documentation site"


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register command with CLI"""
    parser = subparsers.add_parser(
        COMMAND_NAME,
        help=COMMAND_HELP,
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="action")

    # sf docs serve
    serve_parser = sub.add_parser("serve", help="Start development server")
    serve_parser.add_argument(
        "--lan",
        action="store_true",
        help="Bind to 0.0.0.0 for LAN access",
    )
    serve_parser.add_argument(
        "-p", "--port",
        type=int,
        default=8000,
        help="Port number (default: 8000)",
    )

    # sf docs build
    sub.add_parser("build", help="Build static site to site/")

    # sf docs open
    sub.add_parser("open", help="Open docs in browser")

    parser.set_defaults(func=run)


def _check_mkdocs() -> bool:
    """Check if mkdocs is installed"""
    try:
        subprocess.run(
            [sys.executable, "-m", "mkdocs", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _install_deps(project_root: Path) -> int:
    """Install documentation dependencies"""
    req_file = project_root / "requirements-docs.txt"
    if not req_file.exists():
        console.error(f"Requirements file not found: {req_file}")
        return 1

    console.info("Installing documentation dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)],
    )
    return result.returncode


def run(args: argparse.Namespace) -> int:
    """Execute docs command"""
    project_root = paths.project_root()
    action = getattr(args, "action", None)

    # Default action: serve
    if action is None:
        action = "serve"
        args.lan = False
        args.port = 8000

    # Check mkdocs availability
    if not _check_mkdocs():
        console.warning("MkDocs not found. Installing dependencies...")
        ret = _install_deps(project_root)
        if ret != 0:
            console.error("Failed to install dependencies.")
            console.print(f"  Try: pip install -r {project_root}/requirements-docs.txt")
            return 1

        # Verify installation
        if not _check_mkdocs():
            console.error("MkDocs installation failed.")
            return 1

    mkdocs_yml = project_root / "mkdocs.yml"
    if not mkdocs_yml.exists():
        console.error(f"mkdocs.yml not found: {mkdocs_yml}")
        return 1

    if action == "serve":
        addr = "0.0.0.0" if args.lan else "127.0.0.1"
        port = args.port

        if args.lan:
            _show_lan_info(port)

        console.info(f"Starting docs server at http://{addr}:{port}")
        console.print("  Press Ctrl+C to stop")
        console.print()

        cmd = [
            sys.executable, "-m", "mkdocs", "serve",
            "--dev-addr", f"{addr}:{port}",
            "-f", str(mkdocs_yml),
        ]

        try:
            result = subprocess.run(cmd, cwd=project_root)
            return result.returncode
        except KeyboardInterrupt:
            console.print()
            console.info("Server stopped.")
            return 0

    elif action == "build":
        console.info("Building documentation site...")
        cmd = [
            sys.executable, "-m", "mkdocs", "build",
            "-f", str(mkdocs_yml),
        ]
        result = subprocess.run(cmd, cwd=project_root)

        if result.returncode == 0:
            site_dir = project_root / "site"
            console.success(f"Site built: {site_dir}")
        else:
            console.error("Build failed.")

        return result.returncode

    elif action == "open":
        url = f"http://127.0.0.1:8000"
        console.info(f"Opening {url} in browser...")
        webbrowser.open(url)
        return 0

    return 0


def _show_lan_info(port: int) -> None:
    """Show LAN access information"""
    import socket
    try:
        # Get local IP address
        # ローカル IP アドレスを取得
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        console.info(f"LAN access: http://{local_ip}:{port}")
    except OSError:
        console.warning("Could not determine LAN IP address")
