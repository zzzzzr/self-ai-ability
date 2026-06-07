#!/usr/bin/env python3
"""Batch git fetch + pull for direct child directories under a target folder."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "sync-repos-config.json"
VALID_PULL_MODES = ("rebase", "ff-only", "merge")
DEFAULT_PULL_MODE = "rebase"
SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


@dataclass
class Problem:
    path: Path
    reason: str


@dataclass
class Stats:
    scanned: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


def load_config(config_path: Path) -> dict:
    if not config_path.is_file():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_path(path_str: str) -> Path:
    return Path(os.path.expanduser(path_str)).resolve()


def parse_exclude_args(exclude_args: list[str]) -> set[str]:
    names: set[str] = set()
    for item in exclude_args:
        for part in item.split(","):
            part = part.strip()
            if part:
                names.add(part)
    return names


def validate_pull_mode(mode: str) -> str:
    if mode not in VALID_PULL_MODES:
        valid = ", ".join(VALID_PULL_MODES)
        raise SystemExit(f"Error: invalid pull_mode '{mode}'. Valid values: {valid}")
    return mode


def pull_command(pull_mode: str) -> list[str]:
    if pull_mode == "rebase":
        return ["git", "pull", "--rebase"]
    if pull_mode == "ff-only":
        return ["git", "pull", "--ff-only"]
    return ["git", "pull"]


def is_git_repo(path: Path) -> bool:
    git_path = path / ".git"
    return git_path.is_dir() or git_path.is_file()


def is_rebase_in_progress(repo_dir: Path) -> bool:
    git_dir = repo_dir / ".git"
    if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
        return True

    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "rebase-merge"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False

    rebase_path = repo_dir / result.stdout.strip()
    return rebase_path.exists()


def run_git(repo_dir: Path, args: list[str], dry_run: bool) -> tuple[bool, str]:
    command = " ".join(args)
    if dry_run:
        print(f"  [dry-run] {command}")
        return True, ""

    result = subprocess.run(
        args,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    return result.returncode == 0, output


def abort_rebase_if_needed(repo_dir: Path, dry_run: bool) -> None:
    if not is_rebase_in_progress(repo_dir):
        return

    if dry_run:
        print("  [dry-run] git rebase --abort")
        return

    subprocess.run(
        ["git", "rebase", "--abort"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def classify_pull_failure(pull_mode: str, output: str) -> str:
    lowered = output.lower()

    if pull_mode == "ff-only" and (
        "not possible to fast-forward" in lowered
        or "cannot fast-forward" in lowered
    ):
        return "ff_only_rejected"

    if (
        "conflict" in lowered
        or "patch failed" in lowered
        or "resolve all conflicts" in lowered
        or "rebase failed" in lowered
        or "fix conflicts" in lowered
    ):
        return "conflict"

    if (
        "local changes" in lowered
        or "would be overwritten" in lowered
        or "please commit your changes" in lowered
        or "uncommitted changes" in lowered
        or "cannot pull with rebase" in lowered
        or "stash them" in lowered
        or "your local changes to the following files" in lowered
    ):
        return "dirty_worktree"

    return "pull_failed"


def list_child_dirs(target: Path) -> list[Path]:
    children = [item for item in target.iterdir() if item.is_dir()]
    return sorted(children, key=lambda path: path.name)


def sync_repo(
    repo_dir: Path,
    pull_mode: str,
    dry_run: bool,
) -> Problem | None:
    fetch_ok, _fetch_output = run_git(repo_dir, ["git", "fetch", "origin"], dry_run)
    if not fetch_ok:
        return Problem(repo_dir, "fetch_failed")

    pull_ok, pull_output = run_git(repo_dir, pull_command(pull_mode), dry_run)
    if pull_ok:
        return None

    abort_rebase_if_needed(repo_dir, dry_run)
    reason = classify_pull_failure(pull_mode, pull_output)
    if reason == "pull_failed" and is_rebase_in_progress(repo_dir):
        reason = "conflict"
    return Problem(repo_dir, reason)


def print_usage_hint() -> None:
    print(
        "Hint: copy scripts/sync-repos-config.example.json to scripts/sync-repos-config.json "
        "or pass --target PATH",
        file=sys.stderr,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch git fetch + pull for direct child git repositories."
    )
    parser.add_argument(
        "--target",
        help="Parent directory containing child repositories (overrides config target)",
    )
    parser.add_argument(
        "--pull-mode",
        choices=VALID_PULL_MODES,
        help=f"Pull strategy (default: {DEFAULT_PULL_MODE})",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude child folder names; repeatable and comma-separated",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Config file path (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned git commands without executing them",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    target_arg = args.target or config.get("target")
    if not target_arg:
        print("Error: target is required. Set it in config or pass --target PATH.", file=sys.stderr)
        print_usage_hint()
        return 1

    pull_mode = validate_pull_mode(args.pull_mode or config.get("pull_mode") or DEFAULT_PULL_MODE)
    excludes = set(config.get("exclude", [])) | parse_exclude_args(args.exclude)

    target = resolve_path(target_arg)
    if not target.is_dir():
        print(f"Error: target is not a directory: {target}", file=sys.stderr)
        return 1

    stats = Stats()
    problems: list[Problem] = []

    print(SEPARATOR)
    print(f"Target: {target}")
    print(f"Pull mode: {pull_mode}")
    if excludes:
        print(f"Exclude: {', '.join(sorted(excludes))}")
    if args.dry_run:
        print("Mode: dry-run")
    print(SEPARATOR)
    print("")

    for child in list_child_dirs(target):
        stats.scanned += 1
        name = child.name

        if name.startswith("."):
            stats.skipped += 1
            print(f"[skip:hidden] {name}")
            continue

        if name in excludes:
            stats.skipped += 1
            print(f"[skip:excluded] {name}")
            continue

        if not is_git_repo(child):
            stats.skipped += 1
            print(f"[skip:non-git] {name}")
            continue

        print(f"[sync] {name}")
        problem = sync_repo(child, pull_mode, args.dry_run)
        if problem is None:
            stats.updated += 1
            print("  OK")
        else:
            stats.failed += 1
            problems.append(problem)
            print(f"  FAILED ({problem.reason})")
        print("")

    print(SEPARATOR)
    print(
        f"Done. scanned={stats.scanned} updated={stats.updated} "
        f"skipped={stats.skipped} failed={stats.failed}"
    )
    print("")
    print("遇到问题的子目录：")
    if problems:
        reason_width = max(len(item.reason) for item in problems)
        for item in problems:
            print(f"  [{item.reason.ljust(reason_width)}]  {item.path}")
    else:
        print("  （无）")
    print(SEPARATOR)

    return 1 if stats.failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
