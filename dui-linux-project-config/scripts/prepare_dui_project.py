#!/usr/bin/env python3
"""Prepare SDK libraries and assets for a dui-apis-demo-linux project."""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path


ARCH_SUFFIXES = (
    "aarch64",
    "arm64",
    "arm32",
    "armv7",
    "armv7a",
    "x86_64",
    "x86",
)

SDK_TYPES = ("duilite", "duiplus", "dds", "mqbus")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a delivered DUI SDK and project assets into dui-apis-demo-linux."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--delivery", required=True, type=Path)
    parser.add_argument("--customer", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--config-name")
    parser.add_argument("--sdk-dir", type=Path)
    parser.add_argument("--sdk-type")
    parser.add_argument("--version")
    parser.add_argument("--variant")
    parser.add_argument("--arch")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_part(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def find_sdk_dir(delivery: Path) -> Path:
    candidates = [
        path
        for path in delivery.iterdir()
        if path.is_dir() and "sdk" in path.name.lower()
    ]
    if not candidates:
        fail(f"no SDK directory found below {delivery}")
    if len(candidates) > 1:
        names = ", ".join(path.name for path in candidates)
        fail(f"multiple SDK directories found; pass --sdk-dir explicitly: {names}")
    return candidates[0]


def infer_sdk_type(name: str) -> str:
    lower = name.lower()
    for sdk_type in SDK_TYPES:
        if sdk_type in lower:
            return sdk_type
    fail(f"cannot infer SDK type from {name}; pass --sdk-type")


def infer_version(name: str) -> str:
    match = re.search(r"(?:^|[-_])v?(\d+\.\d+\.\d+)(?:$|[-_])", name)
    if match:
        return match.group(1)
    fail(f"cannot infer SDK version from {name}; pass --version")


def infer_variant_arch(name: str, sdk_type: str) -> tuple[str, str]:
    lower = name.lower()
    prefix = f"{sdk_type}-"
    if lower.startswith(prefix):
        platform = name[len(prefix) :]
    else:
        platform = name

    platform = re.sub(r"-sdk.*$", "", platform, flags=re.IGNORECASE)
    platform = re.sub(r"[-_]v?\d+\.\d+\.\d+.*$", "", platform)
    platform = platform.strip("-_")

    for arch in ARCH_SUFFIXES:
        suffix = f"_{arch}"
        if platform.lower().endswith(suffix):
            variant = platform[: -len(suffix)].strip("-_")
            return variant, arch

        suffix = f"-{arch}"
        if platform.lower().endswith(suffix):
            variant = platform[: -len(suffix)].strip("-_")
            return variant, arch

    fail(f"cannot infer variant/arch from {name}; pass --variant and --arch")


def ensure_inside_project(path: Path, project_root: Path) -> None:
    try:
        path.resolve().relative_to(project_root.resolve())
    except ValueError:
        fail(f"refusing to write outside project root: {path}")


def copy_file(src: Path, dest: Path, *, dry_run: bool, overwrite: bool) -> str:
    if dest.exists():
        if filecmp.cmp(src, dest, shallow=False):
            return f"same  {dest}"
        if not overwrite:
            return f"skip  {dest} (exists; pass --overwrite to replace)"

    if dry_run:
        return f"copy  {src} -> {dest}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return f"copy  {src} -> {dest}"


def iter_sdk_files(sdk_dir: Path) -> tuple[list[Path], list[Path]]:
    libs: list[Path] = []
    headers: list[Path] = []
    for path in sdk_dir.iterdir():
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".h":
            headers.append(path)
        elif suffix in {".so", ".a"} or path.name == "build.info":
            libs.append(path)
    return sorted(libs), sorted(headers)


def iter_asset_files(delivery: Path, sdk_dir: Path) -> list[Path]:
    sdk_resolved = sdk_dir.resolve()
    assets: list[Path] = []
    for path in delivery.iterdir():
        if path.resolve() == sdk_resolved:
            continue
        if path.is_file():
            assets.append(path)
    return sorted(assets)


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    delivery = args.delivery.resolve()

    if not project_root.is_dir():
        fail(f"project root does not exist: {project_root}")
    if not (project_root / "build/scripts/pot.json").is_file():
        fail(f"not a dui-apis-demo-linux root: {project_root}")
    if not delivery.is_dir():
        fail(f"delivery directory does not exist: {delivery}")

    sdk_dir = args.sdk_dir.resolve() if args.sdk_dir else find_sdk_dir(delivery)
    if not sdk_dir.is_dir():
        fail(f"SDK directory does not exist: {sdk_dir}")

    sdk_type = args.sdk_type or infer_sdk_type(sdk_dir.name)
    version = args.version or infer_version(sdk_dir.name)
    if args.variant and args.arch:
        variant, arch = args.variant, args.arch
    else:
        inferred_variant, inferred_arch = infer_variant_arch(sdk_dir.name, sdk_type)
        variant = args.variant or inferred_variant
        arch = args.arch or inferred_arch

    sdk_type = normalize_part(sdk_type)
    variant = normalize_part(variant)
    arch = normalize_part(arch)
    customer = normalize_part(args.customer)
    model = normalize_part(args.model)

    version_root = project_root / "repo/libs" / sdk_type / f"{sdk_type}_{version}"
    lib_dest = version_root / variant / arch
    asset_dest = project_root / "repo/assets" / customer / model
    ensure_inside_project(lib_dest, project_root)
    ensure_inside_project(asset_dest, project_root)

    libs, headers = iter_sdk_files(sdk_dir)
    assets = iter_asset_files(delivery, sdk_dir)
    if not libs:
        fail(f"no library/build.info files found in {sdk_dir}")

    print("summary:")
    if args.config_name:
        print(f"  config:   {args.config_name}")
    print(f"  sdk:      {sdk_type} {version} {variant}/{arch}")
    print(f"  libs:     {lib_dest}")
    print(f"  headers:  {version_root}")
    print(f"  assets:   {asset_dest}")
    print()

    for src in libs:
        print(copy_file(src, lib_dest / src.name, dry_run=args.dry_run, overwrite=args.overwrite))

    for src in headers:
        print(copy_file(src, version_root / src.name, dry_run=args.dry_run, overwrite=args.overwrite))

    for src in assets:
        print(copy_file(src, asset_dest / src.name, dry_run=args.dry_run, overwrite=args.overwrite))


if __name__ == "__main__":
    main()
