---
name: dui-alexa-project-delivery
description: "Deliver a Hisense Alexa Linux project end to end: update the SSPE-via-WWE SDK, rebuild MT9616 audio HAL variants, and publish the configured release package with manifest, changelog, and verification. Use when a request spans SSPE static libraries, audio-hal, and final pot.json packaging."
---

# DUI Alexa project delivery

Use this skill for a complete Hisense Alexa delivery in `dui-apis-demo-linux`. The unit of work is the whole dependency chain:

```text
SDK delivery directory
    -> src/sspe-via-wwe/libsspe_wwe_*.a
    -> src/audio-hal/libaudio.aispeech.default.*.so
    -> repo/libs/hal/... + pot.json + changelog
    -> output/hal_<release>_...zip
```

Do not stop after producing an intermediate archive. A delivery is complete only when the release archive has been inspected and the extracted package builds.

## Required inputs

Before mutating files, resolve these values from the request, repository, or delivery directory:

- repository root, normally `/home/wangqiang/repo/duiProMax/dui-apis-demo-linux`;
- SDK delivery directory containing the SSPE package and companion static libraries;
- `pot.json` configuration name, normally `HISENSE_ALEXA_MT9616`;
- target platform and compiler, such as `gcc-arm-13.2.1` with `ALEXA_PRL_VERSION=2.40`;
- customer-facing `release_version`, bundled HAL `sdk_version`, requirement ticket, and delivery date. Infer versions from existing paths and library names only when the local convention makes the value unambiguous; otherwise ask one bundled clarification before changing files.

If a requirement ticket is unavailable, keep an explicit `需求单: 待补充` placeholder in the customer changelog. Never invent a ticket.

## Preflight

1. Read the repository `AGENTS.md` files and this skill's companion `$dui-linux-project-config` skill when final packaging is requested.
2. Run `git status --short` in the repository. Treat existing modifications and untracked files as user state. Do not revert or overwrite unrelated work.
3. Inspect the delivery with `find <delivery> -maxdepth 2 -type f`, the existing `src/sspe-via-wwe/libs/<platform>` directory, `src/audio-hal/3rd/libs/bfwtk2avs/third/<platform>`, `src/audio-hal/aimakefile`, the variant builder, the matching `pot.json` entry, and the matching changelog.
4. Before replacing libraries, record their names, sizes, hashes, and a temporary backup directory. Remove only old files that are part of the replacement set.

## Phase 1: SSPE-via-WWE

1. Map every delivered ARM static library to the project directory. Copy the SSPE header files when their hashes differ. Preserve delivery filenames when they contain an RDZC or release identifier.
2. Update only the target platform block in `src/sspe-via-wwe/aimakefile`. Use exact filenames, including `.a`; include all libraries required by the source and the delivered SDK (`sspe`, wakeup, core, FFT, JSON, auth, CA, and any interface stub that is actually needed).
3. Add `_FILE_OFFSET_BITS=64` and `_TIME_BITS=64` to both `LOCAL_CFLAGS` and `LOCAL_CXXFLAGS` for the 32-bit target when the delivery/toolchain requires them. Do not apply these flags to unrelated target blocks without evidence.
4. Check duplicate symbols before choosing a stub. If `libsspe_external_interface_stub.a` and the real wakeup library both define `wakeup_Nchans_*`, link the real implementation and omit the stub; verify with `nm` and a strict link check.
5. Build both the static archive and the executable/test target with the delivery toolchain. Record compiler warnings separately from failures. Confirm that compile commands contain both time/file macros and that all target-platform link paths exist.
6. Record the exact generated `libsspe_wwe_<platform>_v<version>.<date>.a`. This archive is the input to Phase 2; do not substitute a prior archive.

Completion criterion: the SSPE static archive and test executable build successfully, all delivered ARM libraries match their source hashes, internal SSPE/wakeup symbols resolve to the intended implementations, and the generated archive is available for the next phase.

## Phase 2: audio-hal

1. Replace the contents of `src/audio-hal/3rd/libs/bfwtk2avs/third/<platform>` with the Phase 1 archive and the companion SDK static libraries. Remove stale names only after the replacement map is recorded. Keep headers needed by the wrapper.
2. Update the matching `hisense_alexa_<platform>` block in `src/audio-hal/aimakefile`:
   - use the new archive and SDK filenames;
   - update the HAL version base used in `AUDIO_HAL_VERSION`;
   - keep auth/CA whole-archive handling consistent with the library's symbol model;
   - preserve the existing variant-to-model mapping unless the request changes it;
   - retain `_FILE_OFFSET_BITS=64` and `_TIME_BITS=64` for the 32-bit target.
3. Update `build_hisense_<platform>_variants.py` so its `VERSION_BASE` matches the aimakefile. Run it to build every declared variant. Do not add a new variant unless the request and model set require one.
4. Run the builder's verification. It must check the version string, expected SSPE model set, ARM32 hard-float ELF, SONAME, exported interface, unresolved internal symbols, toolchain identity, and distinct hashes for each variant.
5. Copy each verified `.so` to `repo/libs/hal/<customer>/<platform>_<solution>/<sdk_version>/`, preserving the exact filenames. Verify byte identity after copying.

Completion criterion: every declared audio HAL variant builds and passes the repository verification script; the final library directory contains only the current dependency set; each copied `.so` is byte-identical to the verified build output.

## Phase 3: customer package

1. Update only the matching `pot.json` object. Keep `sdk_version` equal to the HAL directory version and `release_version` equal to the customer package version. Increment the release version for a formal library update unless the request explicitly freezes it.
2. Make every manifest path exist before packaging. Include the four HAL variants, delivered models, Amazon WWE target and x86 libraries when they are part of the package, test tools, scripts, source entry points, and an integration README. Add minimal source dependencies required by the extracted package build, such as `src/common/dui_thread.h`, based on actual compiler errors.
3. Prevent same-basename resource collisions. If two manifest paths flatten to the same package filename, remove the shadowed entry or change the package layout so the effective file is deterministic. Check especially x1/x1f8 wakeup models.
4. Ensure customer-facing source references follow the new package path. If `src/hal/hal_audio.h` hard-codes an old HAL path, update it or patch `build/scripts/pack.sh` minimally so the generated output points to the manifest's current fullref library. Verify the extracted header, not only the source tree.
5. Keep the customer changelog at `changelogs/<CONFIG_NAME>.changelog.md`. Add the newest entry at the top with the exact `release_version` heading and date. List customer-visible libraries, algorithm resources, test tools, documents, and requirement ticket. Do not expose internal packaging paths or mention x86 library details as customer-facing version components.
6. Run both package modes:

   ```bash
   bash ./build/scripts/pack.sh "<CONFIG_NAME>"
   bash ./build/scripts/pack.sh "<CONFIG_NAME>" release
   ```

   For a formal release, inspect the generated zip with `unzip -l`; confirm `changelog.md`, `manifest.txt`, all four HALs, models, test tools, and current paths are present. The package name must contain the configured release version.

Completion criterion: the release zip contains a self-consistent manifest, changelog, release header, current HALs, resources, and executable tools; no old SDK/HAL version path remains.

## Verification gates

Run checks in this order and stop at the first unmet gate:

1. `git diff --check` and JSON parse of `build/scripts/pot.json`.
2. SHA-256 comparison from delivery → SSPE libs → audio-hal third-party libs → HAL output directory → release zip contents.
3. Strict ARM link check for each HAL against its required runtime and `libtinyalsa-master.so`; inspect `readelf -dW` for unexpected unresolved dependencies.
4. Extract the release zip to a temporary directory. Build the extracted target branch with `SDK_TYPE=hal aimake -t <target> -f aimakefile -s <CONFIG_NAME> clean all`. If x86 debug libraries are included, build the extracted x86 branch too.
5. If an x86 file test tool and usable fixture exist, run one short smoke test and verify a valid output WAV. Report this as host smoke testing, not board validation.
6. Check executable bits on test tools, manifest MD5 entries, current `release_version` in `include/aispeech_release_version.h`, and absence of stale version paths.

Report warnings separately from fatal errors. Always state whether MT9616 board recording, online authorization, all microphone/reference layouts, and wakeup-rate testing were performed; host builds do not imply those tests passed.

## Final report

Return:

- the final zip path and SHA-256;
- the SSPE archive name and HAL `sdk_version`/`release_version`;
- the four built variants;
- files changed and old dependencies removed;
- verification commands and results;
- warnings, known runtime requirements, and any unperformed board tests;
- the temporary verification-record path if one was created.

Do not commit or stage changes unless the user separately asks for that operation.
