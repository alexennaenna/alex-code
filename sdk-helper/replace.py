#!/usr/bin/env python3
"""Replace SDK libraries or assets for a dui-apis-demo-linux project.

Usage examples:
    # Replace SDK libs for a project (auto-detect platform from package name)
    python3 scripts/replace.py sdk AGIBOT_GENIE ./duiPlus-90-dev-sz-linux-zhiYuan-release-V1.28.3.s2-20260609170212

    # Replace SDK with explicit platform subdir
    python3 scripts/replace.py sdk AGIBOT_GENIE ./sdk_package --platform-subdir x86_genie

    # Replace assets
    python3 scripts/replace.py assets AGIBOT_GENIE ./delivery_assets/

    # Dry run (show what would be done without copying)
    python3 scripts/replace.py sdk AGIBOT_GENIE ./sdk_package --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

SDK_NAME_PATTERN = re.compile(
    r"duiPlus-(\d+)-dev-sz-(.+?)-(.+?)-release-[Vv]?([\d.]+(?:\.\w+)?)-(\d+)"
)

DUILITE_NAME_PATTERN = re.compile(
    r"duilite-(.+?)-sdk[_-]?([\d.]+)"
)

# Files that should NOT be added to manifest
MANIFEST_EXCLUDE = {"duiPlus.h", "duilite.h", "sspe.map", "symtab.txt"}

# Files that SDK typically doesn't provide but should be preserved
PRESERVE_FILES = {"libasound.so"}


# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def fail(msg: str) -> None:
    print(f"\033[31merror:\033[0m {msg}", file=sys.stderr)
    raise SystemExit(1)


def info(msg: str) -> None:
    print(f"\033[36m>\033[0m {msg}")


def warn(msg: str) -> None:
    print(f"\033[33mwarn:\033[0m {msg}")


def success(msg: str) -> None:
    print(f"\033[32m✓\033[0m {msg}")


# ──────────────────────────────────────────────────────────────────────────────
# pot.json helpers
# ──────────────────────────────────────────────────────────────────────────────

def load_pot(project_root: Path) -> list[dict]:
    pot_path = project_root / "build" / "scripts" / "pot.json"
    if not pot_path.exists():
        fail(f"pot.json not found at {pot_path}")
    with open(pot_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pot(project_root: Path, data: list[dict]) -> None:
    pot_path = project_root / "build" / "scripts" / "pot.json"
    with open(pot_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # pot.json uses 4-space indent per existing convention


def find_project(pot_data: list[dict], project_name: str) -> dict:
    for entry in pot_data:
        if entry.get("name") == project_name:
            return entry
    fail(f"project '{project_name}' not found in pot.json")


# ──────────────────────────────────────────────────────────────────────────────
# SDK package analysis
# ──────────────────────────────────────────────────────────────────────────────

def find_sdk_inner_dir(sdk_path: Path) -> Path:
    """Handle double-nested SDK directories (e.g., pkg/pkg/libs/)."""
    libs_dir = sdk_path / "libs"
    if libs_dir.is_dir():
        return sdk_path

    # Check for nested directory with same or similar name
    candidates = [
        d for d in sdk_path.iterdir()
        if d.is_dir() and (d / "libs").is_dir()
    ]
    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        names = ", ".join(c.name for c in candidates)
        fail(f"multiple inner SDK dirs found: {names}")

    fail(f"no 'libs/' directory found in {sdk_path}")


def parse_duiplus_sdk_name(name: str) -> dict | None:
    """Parse duiPlus SDK package name."""
    m = SDK_NAME_PATTERN.match(name)
    if not m:
        return None
    return {
        "solution_id": int(m.group(1)),
        "platform_raw": m.group(2),
        "customer": m.group(3),
        "version": m.group(4),
        "timestamp": m.group(5),
    }


def infer_platform_type(platform_raw: str) -> str:
    """Infer if this is an x86/linux package or board package."""
    lower = platform_raw.lower()
    if "linux" in lower or "x86" in lower:
        return "x86"
    return "board"


def find_platform_subdirs(manifest: list[str], solution_id: int) -> dict[str, list[str]]:
    """Find all platform subdirs from manifest for a given solution_id.

    Returns: {"x86": ["x86_genie"], "board": ["rk3588_genie"]}
    """
    prefix = f"/libs/duiplus/duiplus_{solution_id}/"
    subdirs = set()
    for item in manifest:
        if item.startswith(prefix):
            # Extract subdir: /libs/duiplus/duiplus_90/rk3588_genie/xxx.so
            rest = item[len(prefix):]
            parts = rest.split("/")
            if len(parts) >= 2:
                subdirs.add(parts[0])

    result = {"x86": [], "board": []}
    for sd in sorted(subdirs):
        if "x86" in sd.lower():
            result["x86"].append(sd)
        else:
            result["board"].append(sd)
    return result


def find_duilite_subdirs(manifest: list[str], version: str) -> list[str]:
    """Find platform subdirs for duilite SDK."""
    prefix = f"/libs/duilite/duilite_{version}/"
    subdirs = set()
    for item in manifest:
        if item.startswith(prefix):
            rest = item[len(prefix):]
            parts = rest.split("/")
            if len(parts) >= 2:
                subdirs.add(parts[0])
    return sorted(subdirs)


# ──────────────────────────────────────────────────────────────────────────────
# File operations
# ──────────────────────────────────────────────────────────────────────────────

def collect_sdk_files(sdk_inner: Path) -> dict[str, list[Path]]:
    """Collect files from SDK package, grouped by category."""
    result = {"libs": [], "libs_ctc": [], "headers": []}

    libs_dir = sdk_inner / "libs"
    if libs_dir.is_dir():
        for f in sorted(libs_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(libs_dir)
            if rel.parts and rel.parts[0] == "ctc":
                result["libs_ctc"].append(f)
            else:
                result["libs"].append(f)

    include_dir = sdk_inner / "include"
    if include_dir.is_dir():
        for f in sorted(include_dir.iterdir()):
            if f.is_file():
                result["headers"].append(f)

    return result


def copy_files(
    files: list[Path],
    dest_dir: Path,
    *,
    dry_run: bool = False,
    overwrite: bool = True,
    base_dir: Path | None = None,
    flatten_ctc_sspe: bool = False,
) -> list[str]:
    """Copy files to destination. Returns list of copied filenames."""
    copied = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    for src in files:
        rel = Path(src.name)
        if base_dir:
            try:
                rel = src.relative_to(base_dir)
            except ValueError:
                rel = Path(src.name)
            if flatten_ctc_sspe and rel.parts and rel.parts[0] == "ctc" and src.name == "libsspe.so":
                rel = Path(src.name)
        dest = dest_dir / rel
        if dest.exists() and not overwrite:
            warn(f"skip (exists): {rel.as_posix()}")
            continue

        if dry_run:
            info(f"[dry-run] would copy: {rel.as_posix()}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            info(f"copied: {rel.as_posix()}")
        copied.append(rel.as_posix())

    return copied


# ──────────────────────────────────────────────────────────────────────────────
# Manifest operations
# ──────────────────────────────────────────────────────────────────────────────

def update_manifest_libs(
    manifest: list[str],
    platform_prefix: str,
    dest_dir: Path,
) -> list[str]:
    """Update one platform's manifest entries without reordering existing items.

    Args:
        manifest: current manifest list
        platform_prefix: e.g. "/libs/duiplus/duiplus_90/x86_genie/"
        dest_dir: actual directory on disk
    """
    disk_files = []
    if dest_dir.is_dir():
        for f in sorted(dest_dir.rglob("*")):
            if not f.is_file():
                continue
            if f.name in MANIFEST_EXCLUDE:
                continue
            disk_files.append(f.relative_to(dest_dir).as_posix())

    disk_file_set = set(disk_files)
    kept_files = set()
    new_manifest = []
    insert_at = None

    for item in manifest:
        if not item.startswith(platform_prefix):
            new_manifest.append(item)
            continue

        rel = item[len(platform_prefix):]
        if rel in disk_file_set and rel not in kept_files:
            new_manifest.append(item)
            kept_files.add(rel)
            insert_at = len(new_manifest)

    missing_entries = [
        platform_prefix + rel for rel in disk_files if rel not in kept_files
    ]
    if missing_entries:
        if insert_at is None:
            insert_at = len(new_manifest)
        new_manifest[insert_at:insert_at] = missing_entries

    return new_manifest


def update_manifest_assets(
    manifest: list[str],
    asset_prefix: str,
    asset_dir: Path,
) -> list[str]:
    """Update manifest entries for assets based on actual disk content."""
    # Remove old asset entries for this prefix
    new_manifest = [
        item for item in manifest
        if not item.startswith(asset_prefix)
    ]

    # Add entries based on actual disk content
    if asset_dir.is_dir():
        for f in sorted(asset_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(asset_dir.parent.parent.parent.parent)
                new_manifest.append("/" + str(rel))

    return new_manifest


def find_replaceable_file(
    new_filename: str,
    dest_dir: Path,
    manifest: list[str],
    asset_prefix: str,
) -> tuple[str, str] | None:
    """Find an old file that the new file is replacing.

    Heuristic: if the new filename shares a recognizable base prefix with an
    existing file (differing only in version/date suffix), treat it as a replacement.

    Returns (old_filename, old_manifest_entry) or None.
    """
    if not dest_dir.is_dir():
        return None

    # Extract a stable prefix from the new filename (up to version/date part)
    # e.g. "sspe_nnaec_ucann_wkp_70mm_ch5_mic4_ref1_outgain4_v2.0.0.170_i45_doa-20260609v2.bin"
    # base prefix could be "sspe_nnaec_ucann_wkp_70mm_ch5_mic4_ref1_outgain4"
    new_stem = Path(new_filename).stem
    new_suffix = Path(new_filename).suffix  # e.g. ".bin"

    # Strategy: find files with same suffix that share a long common prefix
    best_match = None
    best_prefix_len = 0
    min_prefix_len = min(20, len(new_stem) // 2)  # at least half or 20 chars

    for existing in dest_dir.iterdir():
        if not existing.is_file():
            continue
        if existing.name == new_filename:
            continue  # same name = direct overwrite, not a "replacement"
        if existing.suffix != new_suffix:
            continue

        # Find common prefix length
        old_stem = existing.stem
        common_len = 0
        for a, b in zip(new_stem, old_stem):
            if a == b:
                common_len += 1
            else:
                break

        if common_len > best_prefix_len and common_len >= min_prefix_len:
            best_prefix_len = common_len
            old_entry = asset_prefix + existing.name
            if old_entry in manifest:
                best_match = (existing.name, old_entry)

    return best_match


def update_app_config_refs(
    asset_dir: Path,
    replacements: list[tuple[Path, str, str]],
) -> None:
    """Update app_config*.json files: replace old filenames with new ones."""
    # Find all json config files in the asset directory
    config_files = sorted(asset_dir.glob("app_config*.json"))
    if not config_files:
        return

    for config_path in config_files:
        content = config_path.read_text(encoding="utf-8")
        modified = False

        for new_file, old_filename, _ in replacements:
            if old_filename in content:
                content = content.replace(old_filename, new_file.name)
                modified = True
                info(f"{config_path.name}: {old_filename} → {new_file.name}")

        if modified:
            config_path.write_text(content, encoding="utf-8")
            success(f"{config_path.name} updated")


# ──────────────────────────────────────────────────────────────────────────────
# SDK replacement command
# ──────────────────────────────────────────────────────────────────────────────

def cmd_sdk(args: argparse.Namespace) -> None:
    project_root = args.project_root.resolve()
    sdk_path = args.source.resolve()

    if not sdk_path.is_dir():
        fail(f"SDK path does not exist: {sdk_path}")

    # Load project config
    pot_data = load_pot(project_root)
    project = find_project(pot_data, args.project)
    option = project["option"]
    manifest = project["manifest"]

    sdk_type = option.get("sdk_type", "duiplus")
    info(f"Project: {args.project} (sdk_type={sdk_type})")

    # Find inner SDK directory (handle double nesting)
    sdk_inner = find_sdk_inner_dir(sdk_path)
    info(f"SDK inner dir: {sdk_inner}")

    # Collect SDK files
    sdk_files = collect_sdk_files(sdk_inner)
    if not sdk_files["libs"]:
        fail("no library files found in SDK package")

    # Parse SDK package name for metadata
    parsed = parse_duiplus_sdk_name(sdk_path.name)
    if not parsed:
        parsed = parse_duiplus_sdk_name(sdk_inner.name)

    # Determine target platform_subdir
    if args.platform_subdir:
        target_subdir = args.platform_subdir
    elif parsed:
        solution_id = parsed["solution_id"]
        platform_type = infer_platform_type(parsed["platform_raw"])
        subdirs = find_platform_subdirs(manifest, solution_id)

        candidates = subdirs.get(platform_type, [])
        if len(candidates) == 1:
            target_subdir = candidates[0]
        elif len(candidates) > 1:
            print(f"\nMultiple {platform_type} subdirs found:")
            for i, sd in enumerate(candidates, 1):
                print(f"  {i}. {sd}")
            choice = input("Select (number): ").strip()
            try:
                target_subdir = candidates[int(choice) - 1]
            except (ValueError, IndexError):
                fail("invalid selection")
        else:
            fail(
                f"no {platform_type} platform_subdir found in manifest. "
                f"Use --platform-subdir to specify."
            )
    else:
        fail("cannot infer platform_subdir from package name. Use --platform-subdir.")

    # Determine solution_id and dest dir
    if sdk_type == "duiplus":
        solution_id = option.get("duiplus_solution_id")
        if not solution_id:
            fail("duiplus_solution_id not found in project option")
        dest_dir = project_root / "repo" / "libs" / "duiplus" / f"duiplus_{solution_id}" / target_subdir
        manifest_prefix = f"/libs/duiplus/duiplus_{solution_id}/{target_subdir}/"
    elif sdk_type == "duilite":
        version = option.get("sdk_version", "")
        dest_dir = project_root / "repo" / "libs" / "duilite" / f"duilite_{version}" / target_subdir
        manifest_prefix = f"/libs/duilite/duilite_{version}/{target_subdir}/"
    elif sdk_type == "dds":
        version = option.get("sdk_version", "")
        dest_dir = project_root / "repo" / "libs" / "dds" / f"dds_{version}" / target_subdir
        manifest_prefix = f"/libs/dds/dds_{version}/{target_subdir}/"
    else:
        fail(f"unsupported sdk_type: {sdk_type}")

    info(f"Target subdir: {target_subdir}")
    info(f"Dest dir: {dest_dir}")

    # Handle libsspe.so dual source
    libs_to_copy = list(sdk_files["libs"])
    has_root_sspe = any(f.name == "libsspe.so" for f in sdk_files["libs"])
    has_ctc_sspe = any(f.name == "libsspe.so" for f in sdk_files["libs_ctc"])

    if has_root_sspe and has_ctc_sspe and not args.sspe_source:
        print("\nlibsspe.so found in both libs/ and libs/ctc/:")
        print("  1. libs/libsspe.so (default)")
        print("  2. libs/ctc/libsspe.so")
        choice = input("Select (1/2) [1]: ").strip() or "1"
        if choice == "2":
            # Remove root libsspe.so and add ctc version
            libs_to_copy = [f for f in libs_to_copy if f.name != "libsspe.so"]
            ctc_sspe = next(f for f in sdk_files["libs_ctc"] if f.name == "libsspe.so")
            libs_to_copy.append(ctc_sspe)
            info("Using ctc/libsspe.so")
        else:
            info("Using libs/libsspe.so")
    elif args.sspe_source == "ctc" and has_ctc_sspe:
        libs_to_copy = [f for f in libs_to_copy if f.name != "libsspe.so"]
        ctc_sspe = next(f for f in sdk_files["libs_ctc"] if f.name == "libsspe.so")
        libs_to_copy.append(ctc_sspe)
        info("Using ctc/libsspe.so (--sspe-source=ctc)")

    libs_dir = sdk_inner / "libs"

    # Copy SDK runtime files recursively; auxiliary map/symbol files are excluded.
    lib_files_to_copy = [
        f for f in libs_to_copy
        if f.name not in MANIFEST_EXCLUDE
    ]
    header_files_to_copy = sdk_files["headers"]

    # Show summary
    print(f"\n{'='*60}")
    print(f"  Project:   {args.project}")
    print(f"  SDK type:  {sdk_type}")
    print(f"  Platform:  {target_subdir}")
    print(f"  Dest:      {dest_dir}")
    print(f"  Libs:      {len(lib_files_to_copy)} files")
    print(f"  Headers:   {len(header_files_to_copy)} files")
    if parsed:
        print(f"  Version:   {parsed['version']}")
    print(f"{'='*60}\n")

    # List files to copy
    print("Libraries to copy:")
    for f in lib_files_to_copy:
        rel = f.relative_to(libs_dir)
        if rel.parts and rel.parts[0] == "ctc" and f.name == "libsspe.so":
            rel = Path(f.name)
        existing = dest_dir / rel
        status = " (update)" if existing.exists() else " (new)"
        print(f"  {rel.as_posix()}{status}")

    # Check preserved files
    if dest_dir.exists():
        copied_names = {x.name for x in lib_files_to_copy}
        for f in sorted(dest_dir.iterdir()):
            if f.name in PRESERVE_FILES and f.name not in copied_names:
                print(f"  {f.name} (preserved)")

    if header_files_to_copy:
        print("\nHeaders to copy:")
        for f in header_files_to_copy:
            print(f"  {f.name}")

    if not args.dry_run and not args.yes:
        confirm = input("\nProceed? [Y/n]: ").strip().lower()
        if confirm and confirm != "y":
            print("Aborted.")
            return

    # Execute copy
    print()
    copy_files(
        lib_files_to_copy,
        dest_dir,
        dry_run=args.dry_run,
        base_dir=libs_dir,
        flatten_ctc_sspe=True,
    )
    if header_files_to_copy:
        copy_files(header_files_to_copy, dest_dir, dry_run=args.dry_run)

    # Update pot.json
    if not args.dry_run:
        # Update sdk_version
        if parsed and args.update_version:
            old_version = option.get("sdk_version", "")
            new_version = "v" + parsed["version"] if not parsed["version"].startswith("v") else parsed["version"]
            option["sdk_version"] = new_version
            info(f"sdk_version: {old_version} → {new_version}")

        # Update manifest
        if args.update_manifest:
            project["manifest"] = update_manifest_libs(
                manifest, manifest_prefix, dest_dir
            )
            info(f"manifest updated for {manifest_prefix}")

        save_pot(project_root, pot_data)
        success("pot.json saved")

    # Verification
    if not args.dry_run:
        print(f"\n{'─'*60}")
        print("Verification:")
        verify_sdk(dest_dir, manifest_prefix, project["manifest"])


# ──────────────────────────────────────────────────────────────────────────────
# Asset replacement command
# ──────────────────────────────────────────────────────────────────────────────

def cmd_assets(args: argparse.Namespace) -> None:
    project_root = args.project_root.resolve()
    source_path = args.source.resolve()

    if not source_path.is_dir():
        fail(f"source path does not exist: {source_path}")

    # Load project config
    pot_data = load_pot(project_root)
    project = find_project(pot_data, args.project)
    option = project["option"]

    customer = option.get("customer", "")
    model = option.get("model", "")

    if args.customer:
        customer = args.customer
    if args.model:
        model = args.model

    if not customer:
        fail("customer not found in project config and not specified via --customer")

    # Determine asset dest based on manifest existing paths
    manifest = project["manifest"]
    asset_dirs = set()
    for item in manifest:
        if item.startswith("/assets/"):
            parts = item.split("/")
            if len(parts) >= 4:
                asset_dirs.add(f"/assets/{parts[2]}/{parts[3]}")

    if args.asset_subdir:
        dest_subdir = args.asset_subdir
    elif len(asset_dirs) == 1:
        dest_subdir = list(asset_dirs)[0].lstrip("/")
    elif len(asset_dirs) > 1:
        print("\nMultiple asset directories found in manifest:")
        dirs_list = sorted(asset_dirs)
        for i, d in enumerate(dirs_list, 1):
            print(f"  {i}. {d}")
        choice = input("Select (number): ").strip()
        try:
            dest_subdir = dirs_list[int(choice) - 1].lstrip("/")
        except (ValueError, IndexError):
            fail("invalid selection")
    else:
        dest_subdir = f"assets/{customer}/{model}"

    dest_dir = project_root / "repo" / dest_subdir
    info(f"Asset dest: {dest_dir}")

    # Collect source files
    source_files = sorted(f for f in source_path.iterdir() if f.is_file())
    if not source_files:
        fail(f"no files found in {source_path}")

    # Detect replacements: find old files with similar base name
    asset_prefix = "/" + dest_subdir + "/"
    replacements = []  # list of (new_file, old_filename, old_manifest_entry)
    for src in source_files:
        old_match = find_replaceable_file(src.name, dest_dir, manifest, asset_prefix)
        if old_match:
            replacements.append((src, old_match[0], old_match[1]))

    # Show summary
    print(f"\n{'='*60}")
    print(f"  Project:  {args.project}")
    print(f"  Source:   {source_path}")
    print(f"  Dest:     {dest_dir}")
    print(f"  Files:    {len(source_files)}")
    print(f"{'='*60}\n")

    print("Files to copy:")
    for f in source_files:
        existing = dest_dir / f.name
        replace_info = next((r for r in replacements if r[0] == f), None)
        if replace_info:
            print(f"  {f.name} (replaces: {replace_info[1]})")
        elif existing.exists():
            print(f"  {f.name} (update)")
        else:
            print(f"  {f.name} (new)")

    if not args.dry_run and not args.yes:
        confirm = input("\nProceed? [Y/n]: ").strip().lower()
        if confirm and confirm != "y":
            print("Aborted.")
            return

    # Execute copy
    print()
    copy_files(source_files, dest_dir, dry_run=args.dry_run)

    # Remove old files that were replaced
    for _, old_filename, _ in replacements:
        old_path = dest_dir / old_filename
        if old_path.exists() and not args.dry_run:
            old_path.unlink()
            info(f"removed old: {old_filename}")
        elif args.dry_run:
            info(f"[dry-run] would remove old: {old_filename}")

    # Update manifest
    if not args.dry_run and args.update_manifest:
        # Remove old entries and add new ones
        for src, old_filename, old_entry in replacements:
            if old_entry in manifest:
                manifest.remove(old_entry)
                info(f"manifest -: {old_entry}")
            new_entry = asset_prefix + src.name
            if new_entry not in manifest:
                manifest.append(new_entry)
                info(f"manifest +: {new_entry}")

        # Add any remaining new files not part of replacements
        for f in source_files:
            if not any(r[0] == f for r in replacements):
                entry = asset_prefix + f.name
                if entry not in manifest:
                    manifest.append(entry)
                    info(f"manifest +: {entry}")

        save_pot(project_root, pot_data)
        success("pot.json saved")

    # Update app_config references
    if not args.dry_run and replacements:
        update_app_config_refs(dest_dir, replacements)

    success("asset replacement complete")


# ──────────────────────────────────────────────────────────────────────────────
# Verification
# ──────────────────────────────────────────────────────────────────────────────

def verify_sdk(dest_dir: Path, manifest_prefix: str, manifest: list[str]) -> None:
    """Verify manifest-disk consistency."""
    # Files on disk
    disk_files = set()
    if dest_dir.is_dir():
        for f in dest_dir.rglob("*"):
            if f.is_file() and f.name not in MANIFEST_EXCLUDE:
                disk_files.add(f.relative_to(dest_dir).as_posix())

    # Files in manifest for this prefix
    manifest_files = set()
    for item in manifest:
        if item.startswith(manifest_prefix):
            filename = item[len(manifest_prefix):]
            manifest_files.add(filename)

    # Compare
    only_disk = disk_files - manifest_files
    only_manifest = manifest_files - disk_files

    if only_disk:
        for f in sorted(only_disk):
            warn(f"on disk but NOT in manifest: {f}")

    if only_manifest:
        for f in sorted(only_manifest):
            warn(f"in manifest but NOT on disk: {f}")

    if not only_disk and not only_manifest:
        success(f"manifest ↔ disk consistent ({len(disk_files)} files)")
    else:
        warn("manifest-disk inconsistency detected!")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace SDK libraries or assets for dui-apis-demo-linux projects.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path("."),
        help="project root directory (default: current dir)"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── sdk subcommand ──
    sdk_parser = sub.add_parser("sdk", help="Replace SDK libraries")
    sdk_parser.add_argument("project", help="project name in pot.json (e.g. AGIBOT_GENIE)")
    sdk_parser.add_argument("source", type=Path, help="SDK package directory path")
    sdk_parser.add_argument("--platform-subdir", help="target platform subdir (auto-detected if omitted)")
    sdk_parser.add_argument("--sspe-source", choices=["libs", "ctc"], help="libsspe.so source preference")
    sdk_parser.add_argument("--update-version", action="store_true", default=True, help="update sdk_version in pot.json (default: true)")
    sdk_parser.add_argument("--no-update-version", dest="update_version", action="store_false")
    sdk_parser.add_argument("--update-manifest", action="store_true", default=True, help="update manifest in pot.json (default: true)")
    sdk_parser.add_argument("--no-update-manifest", dest="update_manifest", action="store_false")
    sdk_parser.add_argument("--dry-run", action="store_true", help="show what would be done without copying")
    sdk_parser.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompt")

    # ── assets subcommand ──
    assets_parser = sub.add_parser("assets", help="Replace project assets/resources")
    assets_parser.add_argument("project", help="project name in pot.json")
    assets_parser.add_argument("source", type=Path, help="source directory containing assets")
    assets_parser.add_argument("--customer", help="override customer name")
    assets_parser.add_argument("--model", help="override model name")
    assets_parser.add_argument("--asset-subdir", help="explicit asset subdir (e.g. assets/agibot/rk3588)")
    assets_parser.add_argument("--update-manifest", action="store_true", default=True, help="update manifest in pot.json")
    assets_parser.add_argument("--no-update-manifest", dest="update_manifest", action="store_false")
    assets_parser.add_argument("--dry-run", action="store_true", help="show what would be done without copying")
    assets_parser.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompt")

    args = parser.parse_args()

    # Resolve project root
    args.project_root = args.project_root.resolve()
    if not (args.project_root / "build" / "scripts" / "pot.json").exists():
        fail(f"not a valid project root (pot.json not found): {args.project_root}")

    if args.command == "sdk":
        cmd_sdk(args)
    elif args.command == "assets":
        cmd_assets(args)


if __name__ == "__main__":
    main()
