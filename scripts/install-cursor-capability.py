#!/usr/bin/env python3
"""Install one capability from the local Cursor marketplace."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Stats:
    copied: int = 0
    merged: int = 0
    skipped: int = 0


def load_marketplace(repo_root: Path) -> dict:
    manifest_path = repo_root / ".cursor-plugin" / "marketplace.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Error: marketplace manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def resolve_capability(repo_root: Path, manifest: dict, name: str) -> tuple[Path, dict]:
    for plugin in manifest.get("plugins", []):
        if plugin.get("name") == name:
            source = plugin["source"].lstrip("./")
            capability_dir = repo_root / source
            if not capability_dir.is_dir():
                raise SystemExit(f"Error: capability directory not found: {capability_dir}")
            return capability_dir, plugin

    available = ", ".join(sorted(plugin["name"] for plugin in manifest.get("plugins", [])))
    raise SystemExit(f"Error: capability '{name}' not found. Available: {available}")


def load_plugin_config(capability_dir: Path) -> dict:
    config_path = capability_dir / ".cursor-plugin" / "plugin.json"
    if not config_path.is_file():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def ensure_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def copy_file(src: Path, dst: Path, force: bool, stats: Stats, label: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        print(f"  [skip]  {label} (already exists, use --force to overwrite)")
        stats.skipped += 1
        return
    shutil.copy2(src, dst)
    print(f"  [copy]  {label}")
    stats.copied += 1


def copy_tree(src: Path, dst: Path, force: bool, stats: Stats, label: str) -> None:
    if dst.exists():
        if not force:
            print(f"  [skip]  {label} (already exists, use --force to overwrite)")
            stats.skipped += 1
            return
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  [copy]  {label}")
    stats.copied += 1


def install_skills(capability_dir: Path, refs: list[str], target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    for ref in refs:
        src = capability_dir / ref.lstrip("./")
        if not src.exists():
            print(f"  [warn]  skill path not found: {src}")
            continue

        target_root = target_cursor_dir / "skills"
        if src.is_dir() and (src / "SKILL.md").is_file():
            copy_tree(src, target_root / src.name, force, stats, f"skills/{src.name}/ -> .cursor/skills/{src.name}/")
            continue

        if src.is_dir():
            for item in sorted(src.iterdir()):
                if item.is_dir() and (item / "SKILL.md").is_file():
                    copy_tree(item, target_root / item.name, force, stats, f"skills/{item.name}/ -> .cursor/skills/{item.name}/")


def install_agents(capability_dir: Path, refs: list[str], target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    for ref in refs:
        src = capability_dir / ref.lstrip("./")
        if not src.exists():
            print(f"  [warn]  agent path not found: {src}")
            continue

        target_root = target_cursor_dir / "agents"
        if src.is_file():
            copy_file(src, target_root / src.name, force, stats, f"agents/{src.name} -> .cursor/agents/{src.name}")
            continue

        if src.is_dir():
            for item in sorted(src.iterdir()):
                if item.is_file():
                    copy_file(item, target_root / item.name, force, stats, f"agents/{item.name} -> .cursor/agents/{item.name}")


def merge_mcp(src_file: Path, dst_file: Path, force: bool, stats: Stats) -> None:
    if not src_file.is_file():
        print(f"  [warn]  mcp config not found: {src_file}")
        return

    src_data = json.loads(src_file.read_text(encoding="utf-8"))
    src_servers = src_data.get("mcpServers", {})
    if not src_servers:
        return

    if dst_file.is_file():
        dst_data = json.loads(dst_file.read_text(encoding="utf-8"))
    else:
        dst_data = {"mcpServers": {}}

    dst_servers = dst_data.setdefault("mcpServers", {})

    for name, config in src_servers.items():
        existed = name in dst_servers
        if existed and not force:
            print(f"  [skip]  mcp server '{name}' (already exists, use --force to overwrite)")
            stats.skipped += 1
            continue
        dst_servers[name] = config
        action = "overwrite" if existed else "add"
        print(f"  [merge] mcp server '{name}' ({action})")
        stats.merged += 1

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(json.dumps(dst_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_hooks(src_file: Path, dst_file: Path, stats: Stats) -> None:
    if not src_file.is_file():
        print(f"  [warn]  hooks config not found: {src_file}")
        return

    src_data = json.loads(src_file.read_text(encoding="utf-8"))
    src_hooks = src_data.get("hooks", {})
    if not src_hooks:
        return

    if dst_file.is_file():
        dst_data = json.loads(dst_file.read_text(encoding="utf-8"))
    else:
        dst_data = {"version": 1, "hooks": {}}

    dst_hooks = dst_data.setdefault("hooks", {})
    for event, entries in src_hooks.items():
        current_entries = dst_hooks.setdefault(event, [])
        added = 0
        for entry in entries:
            current_entries.append(entry)
            added += 1
        if added:
            print(f'  [merge] hooks "{event}" (+{added})')
            stats.merged += added

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(json.dumps(dst_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install_hook_scripts(hooks_config: Path, target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    script_dir = hooks_config.parent
    if script_dir.name != "hooks":
        candidate = hooks_config.parent / "hooks"
        if candidate.is_dir():
            script_dir = candidate

    if not script_dir.is_dir():
        return

    for script in sorted(script_dir.glob("*.sh")):
        copy_file(script, target_cursor_dir / "hooks" / script.name, force, stats, f"hooks/{script.name} -> .cursor/hooks/{script.name}")


def install_hooks(capability_dir: Path, refs: list[str], target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    for ref in refs:
        src = capability_dir / ref.lstrip("./")
        merge_hooks(src, target_cursor_dir / "hooks.json", stats)
        install_hook_scripts(src, target_cursor_dir, force, stats)


def install_mcp(capability_dir: Path, refs: list[str], target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    for ref in refs:
        src = capability_dir / ref.lstrip("./")
        merge_mcp(src, target_cursor_dir / "mcp.json", force, stats)


def install_commands(capability_dir: Path, refs: list[str], target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    for ref in refs:
        src = capability_dir / ref.lstrip("./")
        if not src.exists():
            print(f"  [warn]  commands path not found: {src}")
            continue

        target_root = target_cursor_dir / "commands"
        if src.is_file() and src.suffix == ".md":
            copy_file(src, target_root / src.name, force, stats,
                      f"commands/{src.name} -> .cursor/commands/{src.name}")
        elif src.is_dir():
            for item in sorted(src.glob("*.md")):
                copy_file(item, target_root / item.name, force, stats,
                          f"commands/{item.name} -> .cursor/commands/{item.name}")


def install_rules(capability_dir: Path, refs: list[str], target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    def cursor_rule_name(rule_file: Path) -> str:
        if rule_file.suffix == ".md":
            return f"{rule_file.stem}.mdc"
        return rule_file.name

    for ref in refs:
        src = capability_dir / ref.lstrip("./")
        if not src.exists():
            print(f"  [warn]  rules path not found: {src}")
            continue

        target_root = target_cursor_dir / "rules"
        if src.is_file() and src.suffix in {".md", ".mdc"}:
            target_name = cursor_rule_name(src)
            copy_file(src, target_root / target_name, force, stats,
                      f"rules/{src.name} -> .cursor/rules/{target_name}")
        elif src.is_dir():
            rule_files = [item for item in src.iterdir() if item.is_file() and item.suffix in {".md", ".mdc"}]
            for item in sorted(rule_files):
                target_name = cursor_rule_name(item)
                copy_file(item, target_root / target_name, force, stats,
                          f"rules/{item.name} -> .cursor/rules/{target_name}")


def install_references(capability_dir: Path, refs: list[str], target_cursor_dir: Path, force: bool, stats: Stats) -> None:
    for ref in refs:
        src = capability_dir / ref.lstrip("./")
        if not src.exists():
            print(f"  [warn]  references path not found: {src}")
            continue

        target_root = target_cursor_dir / "references"
        if src.is_file():
            copy_file(src, target_root / src.name, force, stats,
                      f"references/{src.name} -> .cursor/references/{src.name}")
        elif src.is_dir():
            for item in sorted(src.rglob("*")):
                if item.is_file():
                    rel = item.relative_to(src)
                    copy_file(item, target_root / rel, force, stats,
                              f"references/{rel} -> .cursor/references/{rel}")


def ensure_gitignore_entry(workspace: Path, entry: str) -> bool:
    """Append entry to .gitignore if not already present. Returns True if appended."""
    gitignore = workspace / ".gitignore"
    if gitignore.is_file():
        content = gitignore.read_text(encoding="utf-8")
        # Check for exact line match (with or without trailing newline)
        for line in content.splitlines():
            if line.strip() == entry:
                return False
    else:
        content = ""

    with gitignore.open("a", encoding="utf-8") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        f.write(f"{entry}\n")
    return True


def install_capability(capability_dir: Path, target_cursor_dir: Path, force: bool) -> Stats:
    stats = Stats()
    plugin_config = load_plugin_config(capability_dir)

    skill_refs = ensure_list(plugin_config.get("skills"))
    if not skill_refs and (capability_dir / "skills").is_dir():
        skill_refs = ["./skills"]
    install_skills(capability_dir, skill_refs, target_cursor_dir, force, stats)

    agent_refs = ensure_list(plugin_config.get("agents"))
    if not agent_refs and (capability_dir / "agents").is_dir():
        agent_refs = ["./agents"]
    install_agents(capability_dir, agent_refs, target_cursor_dir, force, stats)

    hook_refs = ensure_list(plugin_config.get("hooks"))
    if not hook_refs:
        if (capability_dir / "hooks" / "hooks.json").is_file():
            hook_refs = ["./hooks/hooks.json"]
        elif (capability_dir / "hooks.json").is_file():
            hook_refs = ["./hooks.json"]
    install_hooks(capability_dir, hook_refs, target_cursor_dir, force, stats)

    mcp_refs = ensure_list(plugin_config.get("mcpServers"))
    if not mcp_refs:
        if (capability_dir / "mcp-cursor.json").is_file():
            mcp_refs = ["./mcp-cursor.json"]
        elif (capability_dir / "mcp.json").is_file():
            mcp_refs = ["./mcp.json"]
    install_mcp(capability_dir, mcp_refs, target_cursor_dir, force, stats)

    cmd_refs = ensure_list(plugin_config.get("commands"))
    if not cmd_refs and (capability_dir / "commands").is_dir():
        cmd_refs = ["./commands"]
    install_commands(capability_dir, cmd_refs, target_cursor_dir, force, stats)

    rule_refs = ensure_list(plugin_config.get("rules"))
    if not rule_refs and (capability_dir / "rules").is_dir():
        rule_refs = ["./rules"]
    install_rules(capability_dir, rule_refs, target_cursor_dir, force, stats)

    ref_refs = ensure_list(plugin_config.get("references"))
    if not ref_refs and (capability_dir / "references").is_dir():
        ref_refs = ["./references"]
    install_references(capability_dir, ref_refs, target_cursor_dir, force, stats)

    return stats


def list_capabilities(manifest: dict) -> None:
    plugins = manifest.get("plugins", [])
    if not plugins:
        print("No capabilities found.")
        return

    print(f"Available capabilities ({len(plugins)}):\n")
    for plugin in plugins:
        cap_type = plugin.get("type", "?")
        version = plugin.get("version", "?")
        description = plugin.get("description", "")
        print(f"  {plugin['name']:22s} {cap_type:6s} v{version:8s}  {description}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install one capability from the local Cursor marketplace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s --list
  %(prog)s example-skill
  %(prog)s example-skill --dest /path/to/project
  %(prog)s example-skill --dest /path/to/project --force
""",
    )
    parser.add_argument("capability", nargs="?", help="Capability name to install")
    parser.add_argument("--list", action="store_true", help="List available capabilities")
    parser.add_argument("--dest", metavar="DIR", help="Target project directory (default: home directory)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files on conflict")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.list and not args.capability:
        raise SystemExit("Error: provide a capability name or use --list")

    repo_root = Path(__file__).resolve().parent.parent
    manifest = load_marketplace(repo_root)

    if args.list:
        list_capabilities(manifest)
        return

    workspace = Path(args.dest).expanduser().resolve() if args.dest else Path.home()
    if not workspace.is_dir():
        raise SystemExit(f"Error: target directory not found: {workspace}")

    target_cursor_dir = workspace / ".cursor"
    capability_dir, capability_meta = resolve_capability(repo_root, manifest, args.capability)

    print(f"Installing capability: {capability_meta['name']} (v{capability_meta.get('version', '?')})")
    print(f"  source: {capability_dir}")
    print(f"  target: {target_cursor_dir}\n")

    stats = install_capability(capability_dir, target_cursor_dir, args.force)

    # If the capability uses rules, try to add .ai-objectives/ to .gitignore
    plugin_config = load_plugin_config(capability_dir)
    has_rules = bool(ensure_list(plugin_config.get("rules")) or (capability_dir / "rules").is_dir())
    if has_rules and args.dest:
        if ensure_gitignore_entry(workspace, ".ai-objectives/"):
            print("  [gitignore] appended .ai-objectives/ to .gitignore")
            stats.merged += 1
        else:
            print("  [gitignore] .ai-objectives/ already in .gitignore")

    print(f"\nDone. copied={stats.copied}, merged={stats.merged}, skipped={stats.skipped}")

    if has_rules and not args.dest:
        print("\nNote: Cursor rules are project-level. The files above were saved to ~/.cursor/rules/ as a local copy.")
        print("To activate in a specific project, re-run with --dest:")
        print(f"  install.sh {args.capability} --dest /path/to/your/project --force")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
