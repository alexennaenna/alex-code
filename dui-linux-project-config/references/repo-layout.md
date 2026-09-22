# dui-apis-demo-linux Layout Notes

## Key Paths

- `build/scripts/pot.json`: project/package configuration entries.
- `aimakefile`: target-specific build configuration and project modules.
- `repo/libs`: SDK libraries grouped by SDK type, version, platform variant, and architecture.
- `repo/assets`: project resources grouped by customer and model.
- `libs`: root-level compatibility link in some checkouts. Do not use it as the SDK copy destination; write to `repo/libs` directly.

## SDK Placement

Use this shape:

```text
repo/libs/<sdk-type>/<sdk-type>_<version>/<variant>/<arch>/
```

Examples:

```text
repo/libs/duilite/duilite_1.73.0/linux_android_r21e/aarch64/
repo/libs/duilite/duilite_1.54.1/android_linux/arm64/
repo/libs/dds/dds_0.2.226/x86/
```

Place shared headers, such as `duilite.h`, at the version root when that is the existing repo pattern:

```text
repo/libs/duilite/duilite_1.73.0/duilite.h
```

Do not overwrite an existing header unless it is identical or the user explicitly asks.

## Asset Placement

Use lower-case customer/model directory names unless nearby projects use a different convention:

```text
repo/assets/<customer>/<model>/
```

Example:

```text
repo/assets/hisense/32x7n/app_config.json
repo/assets/hisense/32x7n/*.bin
```

## Config Naming

Project config names are usually uppercase and underscore-separated, such as `HISENSE_32X7N`.
Match existing entries in `pot.json` and `aimakefile` before adding new fields.
