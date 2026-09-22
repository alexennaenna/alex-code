---
name: dui-linux-project-config
description: Create or update project configurations in dui-apis-demo-linux for delivered DUILite, duiPlus, DDS, or MQBus Linux/Android SDK packages and assets. Use when the user asks to add a new embedded Linux project, copy SDK/resource deliveries into repo/libs and repo/assets, update build/scripts/pot.json or aimakefile, update delivery changelogs, run build/scripts/pack.sh, or repeat the SDK-to-project setup workflow.
---

# DUI Linux Project Config

## Overview

Use this skill for high-frequency dui-apis-demo-linux delivery work: place SDK libraries and assets, add project configuration, verify the build, and avoid damaging existing repo changes.

The repo usually lives under `/home/wangqiang/repo/duiProMax/dui-apis-demo-linux`. Confirm the actual root from the user's path or current workspace before editing.

## Workflow

1. Inspect the worktree first:
   - Run `git status --short` in `dui-apis-demo-linux`.
   - Treat existing modified or untracked files as user work. Do not revert them.
   - Ignore root-level compatibility links unless they directly affect the project setup.

2. Inspect the SDK delivery directory:
   - Find SDK folders and resource files with `find <delivery> -maxdepth 2 -type f`.
   - Parse SDK type, version, variant, and architecture from SDK names when possible.
   - For names like `duilite-linux_android_r21e_aarch64-sdk-v1.73.0`, place libraries under `repo/libs/duilite/duilite_1.73.0/linux_android_r21e/aarch64/`.
   - When the delivery contains both a target-platform SDK and an x86 Linux SDK for debugging, inspect and include both unless the user explicitly excludes x86 support.

3. Place files:
   - SDK libraries go under `repo/libs/<sdk-type>/<sdk-type>_<version>/<variant>/<arch>/`.
   - Generic x86 Linux SDK libraries go under `repo/libs/<sdk-type>/<sdk-type>_<version>/x86/`.
   - SDK headers usually go at `repo/libs/<sdk-type>/<sdk-type>_<version>/`.
   - Assets go under `repo/assets/<customer>/<model>/`, for example `repo/assets/hisense/32x7n/`.
   - Use the helper script when the delivery follows the standard naming pattern.

4. Update project config:
   - Add or update the project entry in `build/scripts/pot.json`.
   - Add or update `aimakefile` only if the project/config pattern requires it.
   - Prefer matching nearby project entries instead of inventing new fields.
   - Use exact relative paths that will exist after packaging.
   - When both target and x86 SDKs are delivered, include both library sets in the project manifest and add matching target-platform and Linux x86 branches in `aimakefile` so the same project can be debugged on x86.
   - For shared standby-wakeup headers such as `mapi_wwe.h`, keep per-project delivery versions sourced from `pot.json` `sdk_version`; patch only the copied output header before compilation/packaging instead of editing the shared source version for one customer.
   - For standby-wakeup projects using shared `mapi_wwe.c`, put project-specific `wakeup_start_format` and `algorithm_mic` in `pot.json` `option`; packaging should patch the copied `output` `mapi_wwe.c`/`mapi_wwe.h` before compilation instead of hard-coding customer wakeup env strings in shared source or adding extra config headers.

5. Update the delivery changelog:
   - For formal deliveries, always inspect `changelogs/<CONFIG_NAME>.changelog.md`; create or update it unless the project is explicitly `pre_research`.
   - Do not create or update a separate version note inside the project resource directory, such as `version_update.md`, by default. Only create or update one when the user explicitly requests it for a major update, and only then include it in the project manifest. Leave an existing resource-directory version note untouched unless the user asks to update or remove it.
   - Match the existing changelog style and add the newest entry at the top with date, update summary, customer-visible modified files, and requirement ticket.
   - For configurations with `option.release_version`, use its exact value in the changelog entry heading, for example `## [1.0.0] - YYYY-MM-DD`. Do not use `sdk_version` or an internal library identifier such as `hal_<customer>_<model>_<version>` as the changelog heading.
   - Treat `release_version` as the customer-facing delivery/package version and `sdk_version` as the bundled SDK or library version. Keep `release_version`, the changelog heading, and the package name consistent; keep `sdk_version` consistent with the delivered SDK/library paths.
   - For formal delivery changes, increment the customer-facing `release_version` by default (following the local version pattern, normally the last numeric segment), unless the user explicitly says not to update the delivery version. Keep `release_version`, the changelog heading, and the package name consistent. Resource/config-only updates should not change `sdk_version` unless the bundled SDK/library version changes.
   - For the first published version of a project, write `### 更改` using this exact structure, replacing the placeholders with customer-visible capabilities:
     ```markdown
     ### 更改
     - 初始版本
     - 支持的特性：
       - <特性1>
       - <特性2>
       - <特性3>
     ```
     Do not add project-creation, resource-reuse, or delivered-file details as peer bullets in this first-release section.
   - Under `### 版本信息`, explicitly enumerate every versioned component included in the manifest. Include the `release_version`, SDK/HAL libraries, algorithm resources such as SSPE/VAD/wakeup models, authorization or third-party libraries, and versioned test applications or documents as applicable. Derive versions from `pot.json`, manifest paths, and filenames; do not replace the list with wording such as “same as the base project.”
   - If the manifest includes Linux x86 debugging libraries, do not mention their filenames, versions, paths, or other library details in the customer-facing changelog. x86 libraries may remain in the manifest and build verification; changelog version information should list only the customer target-platform libraries and other delivered customer-facing components.
   - Do not add `*` to versions automatically. `*` is a manual marker that the user applies to versions not officially used by the customer; use it only when the user explicitly asks.
   - In customer-facing changelogs, list only delivered libraries/assets/docs/API files; do not expose internal packaging files such as `build/scripts/pot.json`, `aimakefile`, build counters, or local delivery paths.
   - Include a `需求单:` item under `说明`; if the ticket is unknown, ask for it or leave an explicit placeholder for the user to fill.

6. Build and verify:
   - Run `bash ./build/scripts/pack.sh "<CONFIG_NAME>"`.
   - When the delivery includes x86 debugging libraries, also verify the Linux x86 aimake branch. For a release package, confirm both the zip and `manifest.txt` list the x86 libraries, unpack it to a temporary directory, and run `SDK_TYPE=<sdk-type> aimake -t linux -f aimakefile -s <CONFIG_NAME> clean all` there.
   - For release/customer delivery verification, run `bash ./build/scripts/pack.sh "<CONFIG_NAME>" release` and inspect the generated zip with `unzip -l`; confirm `changelog.md` and the updated libraries/assets are present.
   - If release packaging copies `changelog.md` but a custom layout step removes it, fix the packaging script minimally so formal release zips retain `changelog.md`.
   - If Android C code hits C99 syntax such as `for (int i = ...)`, add an Android-targeted C flag such as `-std=gnu99` in `aimakefile` rather than editing third-party code first.
   - Report warnings separately from fatal errors.

## Helper Script

Use `scripts/prepare_dui_project.py` to copy the standard delivery layout:

```bash
python3 scripts/prepare_dui_project.py \
  --project-root /home/wangqiang/repo/duiProMax/dui-apis-demo-linux \
  --delivery /path/to/sdk-delivery \
  --customer hisense \
  --model 32x7n
```

Helpful options:

- `--dry-run`: print planned copies without writing.
- `--sdk-dir`: choose a specific SDK directory if the delivery contains multiple.
- `--sdk-type`, `--version`, `--variant`, `--arch`: override parsed values.
- `--config-name`: include the intended config name in the summary.
- `--overwrite`: allow replacing existing destination files. Without it, existing files are left alone unless content is identical.

The script intentionally does not edit `pot.json` or `aimakefile`; those files require project-specific judgment and should be changed manually after comparing existing patterns.

## Safety Rules

- Write SDK files to `repo/libs` directly. Do not use root-level `libs` as the destination because it may be a compatibility link.
- Do not include symlink maintenance or cleanup in a normal project-config task unless the user explicitly asks for it.
- Keep edits scoped to the new project unless the build failure proves a shared fix is required.

## Reference

Read `references/repo-layout.md` when the repo layout or naming conventions are unclear.
