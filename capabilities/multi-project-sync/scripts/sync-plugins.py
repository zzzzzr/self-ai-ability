#!/usr/bin/env python3
"""Sync plugins configuration across multiple projects for both Claude Code and Cursor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CAPABILITY_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = CAPABILITY_DIR / "config" / "sync-config.json"
SETTINGS_SUBDIRS = [".cursor", ".claude"]


def load_targets(config_path: Path) -> list[Path]:
    if not config_path.is_file():
        raise SystemExit(f"Error: config file not found: {config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return [Path(os.path.expanduser(t)) for t in data.get("targets", [])]


def load_plugins_from_file(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Error: plugins file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if "plugins" in data:
        return data["plugins"]
    return data


def load_plugins_from_project(project_path: Path) -> dict:
    for subdir in SETTINGS_SUBDIRS:
        settings_path = project_path / subdir / "settings.json"
        if settings_path.is_file():
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            plugins = data.get("plugins", {})
            if plugins:
                print(f"  Source: {settings_path} ({len(plugins)} plugins)")
                return plugins
    raise SystemExit(
        f"Error: no plugins found in {project_path}/.cursor/settings.json "
        f"or {project_path}/.claude/settings.json"
    )


def merge_plugins(
    target: Path,
    new_plugins: dict,
    force: bool,
    replace: bool,
    platforms: list[str],
) -> dict[str, int]:
    results = {}
    for subdir in platforms:
        settings_path = target / subdir / "settings.json"
        if settings_path.is_file():
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}

        plugins = data.setdefault("plugins", {})
        added = 0
        overwritten = 0
        skipped = 0
        removed = 0

        if replace:
            removed = len(set(plugins.keys()) - set(new_plugins.keys()))
            added = len(set(new_plugins.keys()) - set(plugins.keys()))
            overwritten = len(set(new_plugins.keys()) & set(plugins.keys()))
            data["plugins"] = dict(new_plugins)
        else:
            for key, value in new_plugins.items():
                if key in plugins:
                    if force:
                        plugins[key] = value
                        overwritten += 1
                    else:
                        skipped += 1
                else:
                    plugins[key] = value
                    added += 1
            data["plugins"] = plugins

        settings_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        parts = []
        if added:
            parts.append(f"+{added}")
        if overwritten:
            parts.append(f"~{overwritten}")
        if removed:
            parts.append(f"-{removed}")
        if skipped:
            parts.append(f"={skipped}")
        results[subdir] = {"added": added, "overwritten": overwritten, "skipped": skipped, "removed": removed}
        print(f"    [{subdir:7s}] {' '.join(parts) or 'no change'}")

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync plugins to multiple projects (Claude Code + Cursor).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # Append plugins from a JSON file to all targets
  %(prog)s --from-file plugins-to-add.json

  # Sync plugins from one project to all other targets
  %(prog)s --from-project ~/Documents/for_git/overseas-payment

  # Force overwrite existing plugins
  %(prog)s --from-file plugins-to-add.json --force

  # Only sync to Cursor (skip Claude Code)
  %(prog)s --from-file plugins-to-add.json --platform cursor

  # Only sync to Claude Code (skip Cursor)
  %(prog)s --from-file plugins-to-add.json --platform claude

  # Use a custom targets config
  %(prog)s --from-file plugins-to-add.json --config my-targets.json

  # Dry run — show what would happen without writing
  %(prog)s --from-file plugins-to-add.json --dry-run

  # Replace entire plugins section with standard config (removes extras)
  %(prog)s --from-file plugins-standard.json --replace
""",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-file",
        metavar="FILE",
        help="JSON file containing plugins to add. Can be a full settings.json "
        '(with "plugins" key) or a bare plugins object.',
    )
    source.add_argument(
        "--from-project",
        metavar="DIR",
        help="Source project directory — reads plugins from its .cursor/settings.json "
        "or .claude/settings.json.",
    )

    parser.add_argument(
        "--config",
        metavar="FILE",
        default=str(DEFAULT_CONFIG),
        help=f"Targets config file (default: {DEFAULT_CONFIG.name})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing plugin entries (default: skip existing)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace entire plugins section with the source (removes plugins not in source)",
    )
    parser.add_argument(
        "--platform",
        choices=["cursor", "claude", "both"],
        default="both",
        help="Which platform(s) to sync to (default: both)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )
    parser.add_argument(
        "--exclude",
        metavar="DIR",
        action="append",
        default=[],
        help="Exclude a target path from sync (can be repeated)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Determine platforms
    if args.platform == "cursor":
        platforms = [".cursor"]
    elif args.platform == "claude":
        platforms = [".claude"]
    else:
        platforms = SETTINGS_SUBDIRS

    # Load source plugins
    if args.from_file:
        source_path = Path(args.from_file).expanduser().resolve()
        new_plugins = load_plugins_from_file(source_path)
        print(f"Source: {source_path} ({len(new_plugins)} plugins)")
    else:
        project_path = Path(args.from_project).expanduser().resolve()
        new_plugins = load_plugins_from_project(project_path)

    if not new_plugins:
        raise SystemExit("Error: no plugins to sync")

    # Load targets
    config_path = Path(args.config).expanduser().resolve()
    targets = load_targets(config_path)
    excludes = {Path(os.path.expanduser(e)).resolve() for e in args.exclude}

    # Filter: skip source project itself and excluded paths
    source_resolved = None
    if args.from_project:
        source_resolved = Path(args.from_project).expanduser().resolve()

    filtered_targets = []
    for t in targets:
        resolved = t.resolve()
        if source_resolved and resolved == source_resolved:
            continue
        if resolved in excludes:
            continue
        filtered_targets.append(t)

    if not filtered_targets:
        raise SystemExit("Error: no valid targets after filtering")

    print(f"Targets: {len(filtered_targets)} projects")
    print(f"Platforms: {', '.join(p.strip('.') for p in platforms)}")
    if args.replace:
        mode = "replace (removes plugins not in source)"
    elif args.force:
        mode = "force overwrite"
    else:
        mode = "skip existing"
    print(f"Mode: {mode}")
    if args.dry_run:
        print("DRY RUN — no files will be written\n")
    print()

    # Plugins to sync
    print("Plugins to sync:")
    for key in new_plugins:
        print(f"  - {key}")
    print()

    if args.dry_run:
        all_removals: dict[str, set] = {}
        for target in filtered_targets:
            print(f"  {target}")
            for subdir in platforms:
                settings_path = target / subdir / "settings.json"
                if settings_path.is_file():
                    data = json.loads(settings_path.read_text(encoding="utf-8"))
                    existing = set(data.get("plugins", {}).keys())
                else:
                    existing = set()
                new_keys = set(new_plugins.keys())
                to_add = new_keys - existing
                to_remove = existing - new_keys if args.replace else set()
                to_overwrite = (existing & new_keys) if (args.force or args.replace) else set()
                to_skip = (existing & new_keys) if not (args.force or args.replace) else set()
                parts = []
                if to_add:
                    parts.append(f"+{len(to_add)}")
                if to_overwrite:
                    parts.append(f"~{len(to_overwrite)}")
                if to_remove:
                    parts.append(f"-{len(to_remove)}")
                    all_removals.setdefault(str(target), set()).update(to_remove)
                if to_skip:
                    parts.append(f"={len(to_skip)}")
                print(f"    [{subdir.strip('.'):7s}] {' '.join(parts) or 'no change'}")
        if all_removals:
            all_removed_plugins = set()
            for v in all_removals.values():
                all_removed_plugins.update(v)
            print(f"\n  Will be removed ({len(all_removed_plugins)}):")
            for p in sorted(all_removed_plugins):
                print(f"    - {p}")
        print("\nDry run complete. Run without --dry-run to apply.")
        return

    # Apply
    total_added = 0
    total_overwritten = 0
    total_removed = 0
    for target in filtered_targets:
        print(f"  {target}")
        results = merge_plugins(target, new_plugins, args.force, args.replace, platforms)
        for stats in results.values():
            total_added += stats["added"]
            total_overwritten += stats["overwritten"]
            total_removed += stats.get("removed", 0)

    parts = [f"added={total_added}", f"overwritten={total_overwritten}"]
    if total_removed:
        parts.append(f"removed={total_removed}")
    print(f"\nDone. {', '.join(parts)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
