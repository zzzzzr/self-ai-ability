#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate skill/MCP assets from supported AI hub repos into Codex-friendly locations.

This script focuses on the two easiest migration categories:

1. Skills:
   - source: plugins/<plugin>/skills/<skill>/** or
             capabilities/<capability>/skills/<skill>/**
   - target: ~/.agents/skills/<codex-skill-name>/**

2. MCP:
   - source: plugins/<plugin>/mcp.json | mcp-claude.json | mcp-cursor.json
             capabilities/<capability>/mcp.json | mcp-claude.json | mcp-cursor.json
   - target: a managed block inside ~/.codex/config.toml, or a standalone
     TOML fragment file for manual review.

The script intentionally avoids Cursor/Claude specific hooks/rules/marketplace
logic because those do not map cleanly to Codex.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


MCP_FILENAMES = ("mcp-cursor.json", "mcp-claude.json", "mcp.json")
MANAGED_BEGIN = "# >>> codex-skill-migrator MCP >>>"
MANAGED_END = "# <<< codex-skill-migrator MCP <<<"


@dataclass(frozen=True)
class SkillSpec:
    plugin_name: str
    skill_name: str
    source_dir: Path
    target_name: str


@dataclass
class SkillResult:
    installed: List[Tuple[str, Path]]
    skipped: List[Tuple[str, str]]


@dataclass
class McpServerSpec:
    name: str
    plugin_name: str
    raw: dict


@dataclass(frozen=True)
class SourceLayout:
    root_dir_name: str
    unit_label: str


def repo_root_from_script() -> Path:
    return Path.cwd()


def resolve_source_layout(repo_root: Path, requested_layout: str) -> SourceLayout:
    if requested_layout == "plugins":
        return SourceLayout(root_dir_name="plugins", unit_label="plugin")
    if requested_layout == "capabilities":
        return SourceLayout(root_dir_name="capabilities", unit_label="capability")

    plugins_root = repo_root / "plugins"
    capabilities_root = repo_root / "capabilities"
    if plugins_root.is_dir() and capabilities_root.is_dir():
        raise SystemExit(
            "Both plugins/ and capabilities/ exist. "
            "Please pass --source-layout plugins or --source-layout capabilities."
        )
    if plugins_root.is_dir():
        return SourceLayout(root_dir_name="plugins", unit_label="plugin")
    if capabilities_root.is_dir():
        return SourceLayout(root_dir_name="capabilities", unit_label="capability")
    raise SystemExit(
        f"Neither plugins/ nor capabilities/ found under repo root: {repo_root}"
    )


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return cleaned or "unnamed"


def default_target_name(plugin_name: str, skill_name: str) -> str:
    plugin_slug = slugify(plugin_name)
    skill_slug = slugify(skill_name)
    if plugin_slug == skill_slug:
        return plugin_slug
    return f"{plugin_slug}-{skill_slug}"


def iter_unit_dirs(units_root: Path) -> Iterable[Path]:
    for item in sorted(units_root.iterdir()):
        if item.is_dir():
            yield item


def collect_available_units(units_root: Path) -> List[str]:
    return [path.name for path in iter_unit_dirs(units_root)]


def resolve_selected_units(
    units_root: Path,
    requested: List[str],
    include_all: bool,
    unit_label: str,
) -> List[Path]:
    available = {path.name: path for path in iter_unit_dirs(units_root)}
    if include_all:
        return list(available.values())
    if not requested:
        raise SystemExit(
            f"No {unit_label} selected. Use --plugin <name> or --all."
        )

    missing = [name for name in requested if name not in available]
    if missing:
        raise SystemExit(
            "Unknown {}(s): {}. Available: {}".format(
                unit_label,
                ", ".join(missing), ", ".join(sorted(available))
            )
        )
    return [available[name] for name in requested]


def collect_skills(plugin_dirs: Iterable[Path], prefix_mode: str) -> List[SkillSpec]:
    specs: List[SkillSpec] = []
    for plugin_dir in plugin_dirs:
        skills_root = plugin_dir / "skills"
        if not skills_root.is_dir():
            continue
        for skill_md in sorted(skills_root.glob("*/SKILL.md")):
            skill_dir = skill_md.parent
            skill_name = skill_dir.name
            plugin_name = plugin_dir.name
            if prefix_mode == "never":
                target_name = slugify(skill_name)
            elif prefix_mode == "always":
                target_name = default_target_name(plugin_name, skill_name)
            else:
                target_name = default_target_name(plugin_name, skill_name)
            specs.append(
                SkillSpec(
                    plugin_name=plugin_name,
                    skill_name=skill_name,
                    source_dir=skill_dir,
                    target_name=target_name,
                )
            )
    return specs


def install_skills(skills: List[SkillSpec], target_root: Path, force: bool, dry_run: bool) -> SkillResult:
    installed: List[Tuple[str, Path]] = []
    skipped: List[Tuple[str, str]] = []

    target_root.mkdir(parents=True, exist_ok=True)

    seen_targets: Dict[str, SkillSpec] = {}
    for spec in skills:
        if spec.target_name in seen_targets:
            other = seen_targets[spec.target_name]
            raise SystemExit(
                "Skill name collision after migration naming: "
                f"{other.plugin_name}/{other.skill_name} and "
                f"{spec.plugin_name}/{spec.skill_name} -> {spec.target_name}. "
                "Use a different naming strategy."
            )
        seen_targets[spec.target_name] = spec

    for spec in skills:
        target_dir = target_root / spec.target_name
        source_label = f"{spec.plugin_name}/{spec.skill_name}"
        if target_dir.exists():
            if not force:
                skipped.append((source_label, "target exists"))
                continue
            if not dry_run:
                shutil.rmtree(target_dir)

        if not dry_run:
            shutil.copytree(spec.source_dir, target_dir)
        installed.append((source_label, target_dir))

    return SkillResult(installed=installed, skipped=skipped)


def choose_mcp_file(plugin_dir: Path, prefer_cursor: bool) -> Optional[Path]:
    ordered = list(MCP_FILENAMES)
    if not prefer_cursor:
        ordered = ["mcp-claude.json", "mcp-cursor.json", "mcp.json"]
    for name in ordered:
        candidate = plugin_dir / name
        if candidate.is_file():
            return candidate
    return None


def collect_mcp_servers(plugin_dirs: Iterable[Path], prefer_cursor: bool) -> List[McpServerSpec]:
    specs: List[McpServerSpec] = []
    for plugin_dir in plugin_dirs:
        mcp_file = choose_mcp_file(plugin_dir, prefer_cursor=prefer_cursor)
        if mcp_file is None:
            continue
        with open(mcp_file, encoding="utf-8") as f:
            payload = json.load(f)
        servers = payload.get("mcpServers", {})
        if not isinstance(servers, dict):
            continue
        for server_name, server_body in servers.items():
            if not isinstance(server_body, dict):
                continue
            specs.append(
                McpServerSpec(
                    name=server_name,
                    plugin_name=plugin_dir.name,
                    raw=server_body,
                )
            )
    return specs


def normalize_env_placeholders(value: str) -> str:
    return re.sub(r"\$\{env:([A-Za-z_][A-Za-z0-9_]*)\}", r"${\1}", value)


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def toml_string(value: str) -> str:
    return f'"{toml_escape(value)}"'


def toml_array(values: List[str]) -> str:
    return "[" + ", ".join(toml_string(v) for v in values) + "]"


def render_mcp_block(servers: List[McpServerSpec]) -> str:
    merged: Dict[str, McpServerSpec] = {}
    conflicts: List[str] = []
    for spec in servers:
        if spec.name in merged:
            current = merged[spec.name]
            if current.raw != spec.raw:
                conflicts.append(
                    f"{spec.name} (from {current.plugin_name} and {spec.plugin_name})"
                )
            continue
        merged[spec.name] = spec

    if conflicts:
        raise SystemExit(
            "Found conflicting MCP server definitions: {}. "
            "Resolve the source plugins before migrating.".format(", ".join(conflicts))
        )

    lines: List[str] = [MANAGED_BEGIN, "# Generated by codex-skill-migrator", ""]
    for server_name in sorted(merged):
        spec = merged[server_name]
        body = spec.raw
        lines.append(f'# source: plugin "{spec.plugin_name}"')
        lines.append(f"[mcp_servers.{server_name}]")

        if "url" in body and isinstance(body["url"], str):
            lines.append(f"url = {toml_string(normalize_env_placeholders(body['url']))}")
        if "command" in body and isinstance(body["command"], str):
            lines.append(f"command = {toml_string(body['command'])}")
        if "args" in body and isinstance(body["args"], list):
            args = [str(arg) for arg in body["args"]]
            lines.append(f"args = {toml_array(args)}")
        if "enabled" in body and isinstance(body["enabled"], bool):
            lines.append(f"enabled = {'true' if body['enabled'] else 'false'}")
        if "startup_timeout_sec" in body:
            timeout = body["startup_timeout_sec"]
            if isinstance(timeout, (int, float)):
                lines.append(f"startup_timeout_sec = {timeout}")
        if "env" in body and isinstance(body["env"], dict) and body["env"]:
            lines.append("")
            lines.append(f"[mcp_servers.{server_name}.env]")
            for key in sorted(body["env"]):
                value = str(body["env"][key])
                lines.append(f"{key} = {toml_string(normalize_env_placeholders(value))}")
        lines.append("")

    lines.append(MANAGED_END)
    lines.append("")
    return "\n".join(lines)


def write_mcp_fragment(fragment_text: str, output_path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(fragment_text, encoding="utf-8")


def merge_mcp_into_codex_config(fragment_text: str, config_path: Path, dry_run: bool) -> None:
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    pattern = re.compile(
        re.escape(MANAGED_BEGIN) + r".*?" + re.escape(MANAGED_END) + r"\n?",
        re.S,
    )
    if pattern.search(existing):
        updated = pattern.sub(fragment_text, existing)
    else:
        separator = "\n" if existing and not existing.endswith("\n") else ""
        updated = f"{existing}{separator}{fragment_text}"

    if dry_run:
        return
    backup_path = config_path.with_suffix(config_path.suffix + ".bak.migrator")
    if config_path.exists():
        shutil.copy2(config_path, backup_path)
    config_path.write_text(updated, encoding="utf-8")


def print_skill_summary(result: SkillResult) -> None:
    print("Skills")
    for source_label, target_dir in result.installed:
        print(f"  [install] {source_label} -> {target_dir}")
    for source_label, reason in result.skipped:
        print(f"  [skip]    {source_label} ({reason})")
    print(
        f"  installed: {len(result.installed)}, skipped: {len(result.skipped)}"
    )


def print_mcp_summary(
    servers: List[McpServerSpec],
    fragment_output: Optional[Path],
    applied: bool,
    dry_run: bool,
) -> None:
    print("MCP")
    deduped_names = sorted({spec.name for spec in servers})
    for name in deduped_names:
        plugins = sorted({spec.plugin_name for spec in servers if spec.name == name})
        print(f"  [server]  {name} (from {', '.join(plugins)})")
    print(f"  servers: {len(deduped_names)}")
    if fragment_output is not None:
        print(f"  fragment: {fragment_output}")
    if applied:
        if dry_run:
            print("  config:   would merge into ~/.codex/config.toml managed block")
        else:
            print("  config:   merged into ~/.codex/config.toml managed block")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate skills and MCP config from AI hub repos into Codex."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root_from_script(),
        help="Path to the source repository root.",
    )
    parser.add_argument(
        "--source-layout",
        choices=("auto", "plugins", "capabilities"),
        default="auto",
        help="Source root layout. Default auto-detects plugins/ or capabilities/.",
    )
    parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin/capability name to migrate. Repeatable.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Migrate all plugins.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available plugins and exit.",
    )
    parser.add_argument(
        "--skills-target",
        type=Path,
        default=Path.home() / ".agents" / "skills",
        help="Destination directory for Codex user skills.",
    )
    parser.add_argument(
        "--codex-config",
        type=Path,
        default=Path.home() / ".codex" / "config.toml",
        help="Codex config.toml path for MCP merge.",
    )
    parser.add_argument(
        "--mcp-fragment-output",
        type=Path,
        default=None,
        help="Where to write the generated MCP TOML fragment. Defaults to <repo-root>/out/codex-mcp.toml.",
    )
    parser.add_argument(
        "--skill-prefix-mode",
        choices=("always", "never", "auto"),
        default="always",
        help="How to name migrated Codex skills. Default keeps plugin prefix to avoid collisions.",
    )
    parser.add_argument(
        "--prefer",
        choices=("cursor", "claude"),
        default="cursor",
        help="Preferred MCP source file when both mcp-cursor.json and mcp-claude.json exist.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing migrated skills.",
    )
    parser.add_argument(
        "--apply-mcp",
        action="store_true",
        help="Merge MCP fragment into ~/.codex/config.toml managed block.",
    )
    parser.add_argument(
        "--skills-only",
        action="store_true",
        help="Only migrate skills.",
    )
    parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="Only migrate MCP.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing files.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    source_layout = resolve_source_layout(repo_root, args.source_layout)
    units_root = repo_root / source_layout.root_dir_name

    if args.list:
        for unit_name in collect_available_units(units_root):
            print(unit_name)
        return 0

    if args.skills_only and args.mcp_only:
        raise SystemExit("--skills-only and --mcp-only cannot be used together.")

    selected_plugins = resolve_selected_units(
        units_root, args.plugin, args.all, source_layout.unit_label
    )

    run_skills = not args.mcp_only
    run_mcp = not args.skills_only

    if args.mcp_fragment_output is None:
        fragment_output = repo_root / "out" / "codex-mcp.toml"
    else:
        fragment_output = args.mcp_fragment_output

    if run_skills:
        skills = collect_skills(selected_plugins, prefix_mode=args.skill_prefix_mode)
        skill_result = install_skills(
            skills=skills,
            target_root=args.skills_target,
            force=args.force,
            dry_run=args.dry_run,
        )
        print_skill_summary(skill_result)
    else:
        skill_result = SkillResult(installed=[], skipped=[])

    if run_mcp:
        mcp_servers = collect_mcp_servers(
            selected_plugins, prefer_cursor=(args.prefer == "cursor")
        )
        fragment_text = render_mcp_block(mcp_servers)
        write_mcp_fragment(fragment_text, fragment_output, dry_run=args.dry_run)
        if args.apply_mcp:
            merge_mcp_into_codex_config(
                fragment_text, args.codex_config, dry_run=args.dry_run
            )
        print_mcp_summary(
            mcp_servers,
            fragment_output if run_mcp else None,
            applied=args.apply_mcp,
            dry_run=args.dry_run,
        )

    if not run_skills and not run_mcp:
        raise SystemExit("Nothing selected to migrate.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
