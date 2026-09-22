---
name: sdk-helper
description: SDK和资源替换助手。支持替换duiplus/duilite SDK库文件、替换项目资源，自动更新pot.json、app_config和changelog。可通过AI调用或直接运行Python脚本。
metadata:
  targets: [qoder, universal]
---

# SDK 助手

## 触发条件

用户需要替换 SDK 库文件或项目资源（.bin/.json 等），并指定项目名（pot.json 中的 `name` 字段）。

## 独立脚本

脚本位于用户级 Skillshare 源的 `sdk-helper/replace.py`，可脱离 Codex 和 Qoder 独立执行。以下命令默认在目标项目根目录执行：

```bash
# 替换 SDK 库（目标平台已明确时才可执行；多平台项目建议显式指定 --platform-subdir）
python3 ~/.config/skillshare/skills/sdk-helper/replace.py sdk <项目名> <SDK包目录>

# 替换资源文件
python3 ~/.config/skillshare/skills/sdk-helper/replace.py assets <项目名> <资源目录>

# 常用选项
#   --platform-subdir <name>   手动指定平台子目录
#   --sspe-source {libs,ctc}   指定 libsspe.so 来源
#   --dry-run                  预览模式，不实际拷贝
#   -y                         跳过确认
#   --no-update-version        不更新 sdk_version
#   --no-update-manifest       不更新 manifest
```

---

## 项目布局

```text
build/scripts/pot.json       # 项目配置主入口（manifest、sdk_version）
aimakefile                   # 构建配置（rpath、链接库）
changelogs/{NAME}.changelog.md  # 项目变更记录
repo/libs/                   # SDK 库（按 sdk_type/solution_id/platform_subdir 分层）
repo/assets/                 # 项目资源（按 customer/model 分层）
```

### SDK 库路径

```text
repo/libs/duiplus/duiplus_{solution_id}/{platform_subdir}/
```

示例：`duiplus_90/rk3588_genie/`、`duiplus_90/x86_genie/`、`duiplus_45/nvidia_aarch64/`

### 头文件

`duiPlus.h` 放在 `platform_subdir` 目录下（与 .so 同级），**不加入 manifest**。

---

## SDK 包名解析

格式：`duiPlus-{solution_id}-dev-sz-{platform}-{customer}-release-{version}-{timestamp}`

| 字段 | 推断规则 |
|------|----------|
| `{platform}` 含 `linux` | 对应 x86 相关 `platform_subdir` |
| `{platform}` 为具体平台 | 对应板端 `platform_subdir`（如 `rk3588s_gcc_9.2` → `rk3588_genie`） |
| `{version}` | 更新 pot.json 的 `sdk_version`（如 `V1.28.3.s2` → `v1.28.3.s2`） |

**注意**：
- SDK 包名中的 `{platform}` 只能作为候选平台参考，不能替代用户确认。
- linux SDK 对应的 `platform_subdir` 不一定叫 `x86`，需从 manifest 现有条目推断。
- 当项目同时存在 linux/x86 与板端平台目录时，用户只说“替换 SDK”“测试新 SDK”而未明确目标平台，必须先询问用户要替换到 linux/x86 还是板端（如 ssd202/rk3588），不得仅凭包名自动落盘。

---

## 执行流程

### 全局影响检查规则

任何源码、宏、配置、SDK、资源或构建脚本改动，禁止只按当前报错文件局部处理。编辑前必须先做全局扫描，并先向用户说明影响范围，再实施修改：

1. 用 `rg` 查找被改符号、宏、字段、资源名的定义、引用、调用方和配置引用，沿“输入/生产者 -> FIFO/缓存 -> 消费者/feed -> SDK/输出”链路检查。
2. 对比所有受影响项目、平台、编译分支和交付 manifest，明确会受影响、刻意不改的内容，以及共享文件、合并、ABI 和 rpath 风险。
3. 同时检查实时、离线、短读、异常和结束路径，核对采样率、通道数、位宽、长度计算、内存边界和线程生命周期。
4. 修改前报告影响、风险、联动文件和验证方式；公共代码可能波及时，先说明最小兼容方案，不默认扩散改动。
5. 修改后按影响面验证 `git diff --check`、相关平台编译、manifest/配置一致性及运行时依赖，并汇报已验证项和未验证风险。

用户只要求评估时不得擅自修改业务代码；要求实施时也必须先完成上述影响说明。

### 强制收尾规则

凡是使用本 skill 完成 SDK、资源、app_config、pot.json、aimakefile、源码兼容改动或新增项目后，**必须更新或校正 `changelogs/{PROJECT_NAME}.changelog.md`**，不得省略。

- changelog 必须记录本次实际落地的资源名、SDK 版本、配置文件、源码文件等内容，不能沿用旧文件名或猜测文件名。
- changelog 顶部版本号必须使用**交付版本**，不要使用 SDK 版本号；格式参考未来居：`## [v1.0.1] - 2026-07-27`，并在“版本信息”中写 `交付版本: 1.0.1`。
- 交付版本需要基于当前项目 changelog 已有交付版本向上迭代；若已有最高交付版本为 `1.0.0`，本次新增条目用 `1.0.1`，以此类推。
- 新项目当天仍处于初始版本整理阶段、`v1.0.0` 尚未正式交付或提交时，同批 SDK、资源和配置调整继续合并到 `v1.0.0`，不要新增 `v1.0.1`；只有上一交付版本已经形成后，后续更新才向上迭代。
- 若资源名、SDK 包名、manifest、app_config 在过程中反复调整，最终收尾时必须重新核对磁盘文件和配置引用，并以最终状态重写/修正 changelog 条目。
- changelog 所需的需求单链接、说明信息、SDK 来源链接等缺失时，必须先主动向用户索取；用户暂时没有、明确跳过或短时间内未补充时，再写 changelog 条目并标注“待补充”，同时在最终回复里提醒用户补齐。
- x86 仅验证的中间状态也要记录；可标注“仅 x86 验证，板端尚未替换”，但不能完全不写。
- 最终回复前必须明确检查并汇报 changelog 已更新；若确实不能更新，必须说明阻塞原因。

### 替换 SDK

1. **定位配置** — grep pot.json 获取 `duiplus_solution_id`、`sdk_version`、所有 `platform_subdir`
2. **确认目标平台** — 若 manifest 中同一项目同时有 linux/x86 与板端目录，且用户未明确说明目标平台，必须先问“替换到 linux/x86 还是板端（具体平台名）”；确认前禁止拷贝 SDK、修改 pot.json、修改 changelog
3. **列出 SDK 文件** — `find <sdk_path> -path "*/libs/*" -type f | sort`（不要用 `.so$` 过滤）
4. **列出 repo 现有文件** — `ls -la` 目标目录
5. **对比差异** — 确认新增/替换/保留的文件
6. **执行拷贝** — cp .so 和 .h 到目标目录
7. **更新 pot.json** — sdk_version + manifest；除非用户明确要求切换编译/测试平台，否则不要改 `platform` / `aimake_type`
8. **更新 aimakefile** — 检查 rpath 是否需调整
9. **更新 app_config** — 若资源文件名变化，同步更新引用
10. **更新 changelog** — 记录变更（见下方规范）
11. **验证** — manifest ↔ 磁盘一致性检查

### 替换资源

1. **定位配置** — 从 pot.json manifest 确定 assets 目标目录
2. **拷贝新文件** — 到 `repo/assets/{customer}/{model}/`
3. **删除旧文件** — 若新文件替代了旧版本（文件名前缀匹配）
4. **更新 pot.json manifest** — 替换/新增条目
5. **更新 app_config** — grep 旧文件名，替换为新文件名（所有 `app_config*.json`）
6. **更新 changelog** — 记录变更
7. **验证**

---

## 关键规则

### libsspe.so 来源

若 SDK 同时提供 `libs/libsspe.so` 和 `libs/ctc/libsspe.so`：
- **询问用户**选择哪个
- 仅保留一个，manifest 和 aimakefile rpath 需对应调整

### libasound.so

SDK 不提供此文件。repo 中已有且 manifest 已声明的，**保留不动**。

### libonnxruntime.so 版本号文件

`libonnxruntime.so.1.11.1` 必须作为独立文件拷贝和声明，find 不能用 `.so$` 过滤。

### SDK 子目录运行时文件

SDK 包中 `libs/` 下的子目录也可能包含 SDK 运行时内容，不能只复制顶层 `.so`。例如 `libs/ce/` 下的运行时库必须随平台 SDK 一起复制到目标平台目录，并同步加入 manifest：
- `./libs/duiplus/duiplus_{id}/{platform_subdir}/ce/libsspe.so`

替换 SDK 时必须检查 `libs/` 下的子目录文件，不能只按顶层 `*.so` 拷贝；`sspe.map` 和 `symtab.txt` 属于辅助文件，统一忽略，不复制到交付包、不加入 manifest。

### 多平台

每个 SDK 包对应一个 `platform_subdir`，逐个替换。同一项目可能有多个平台。

### 单平台 / 分步替换

实际工作中常遇到**用户只提供一个 SDK 包**的场景（并非每次都同时给 linux + 板端两个包）：

| 场景 | SDK 包 platform 字段 | 替换目标 platform_subdir | 用途 |
|------|---------------------|--------------------------|------|
| 只换 linux SDK | 含 `linux` | x86 验证目录（如 `x86_bymiot`、`x86_genie`） | x86 编译验证 |
| 只换板端 SDK | 具体平台（如 `ssd202`、`rk3588s_gcc_9.2`） | 板端目录（如 `ssd202_bymiot`、`rk3588_genie`） | 板端交付 |

**推荐的分步替换工作流：**

1. **先换 linux SDK** → 只替换 x86 验证目录 + 该目录的 `duiPlus.h` → 直接进行 x86 编译验证（platform 保持 x86）
2. **验证通过后** → 再换板端 SDK → 替换板端目录 + 该目录的 `duiPlus.h` → 最终交付

**关键注意事项：**
- **目标平台不明确必须先问**：多平台项目中，SDK 包名的 `linux`、`ssd202`、`rk3588` 等字段不能单独决定替换目标；用户未明确时，先确认 `platform_subdir`，例如 `x86_bymiot` 还是 `ssd202_bymiot`
- **只替换一个平台时，另一个平台保持不动**（此时两平台版本暂时不一致，属正常验证阶段，无需报警）
- **每个平台目录各自维护头文件**：换 linux SDK 时同步更新 x86 目录的 `duiPlus.h`；换板端 SDK 时同步更新板端目录的 `duiPlus.h`（头文件与 .so 同级，不跨平台共享）
- **最终交付前**：必须确认两个平台都已更新到目标版本，避免只换了 x86 验证库就交付
- **不要顺手切编译平台**：替换 SDK 不等于修改 `pot.json` 当前 `platform` / `aimake_type`；只有用户明确说要切到 x86 验证、板端验证或恢复平台时才修改
- **sdk_version 更新**：只换 linux SDK 做验证时即可更新 `sdk_version`（验证的就是新版本），但须明确告知用户"仅完成 x86 验证，板端库尚未替换"
- **changelog**：即使仅处于验证阶段也必须记录，并标注"仅 x86 验证，板端库尚未替换"；后续板端替换完成后再更新同一条或新增条目补全最终状态
- **独立脚本使用约束**：只有目标平台已明确或项目只有一个候选平台时，才可直接运行 `python3 replace.py sdk <项目> <单个SDK包>`；多平台项目必须加 `--platform-subdir <name>` 或先向用户确认

### manifest 一致性

- manifest 中每个路径必须在磁盘上真实存在
- 磁盘上每个 .so 必须在 manifest 中有条目（`duiPlus.h` 除外）
- `sspe.map` 和 `symtab.txt` 统一忽略，不加入 manifest
- 磁盘不存在的文件必须从 manifest 删除
- 更新 manifest 时保留现有条目顺序；只删除失效项，并将新增文件追加到对应平台原有条目段末尾，禁止先删除整段再排序重建，避免产生无意义 diff

### 资源替换同步 app_config

替换 .bin 资源时，必须 grep 搜索 `app_config*.json` 中对旧文件名的引用并替换：
- `sspeBinPath`、`wakeupBinPath`、`vadBinPath` 等 `*BinPath` / `*Path` 字段
- 同一项目可能有多个 app_config（如 `app_config_rk3588.json` + `app_config_x86.json`）

### x86 实验 recorder 固定八通道

`app_config_x86.json` 是实验验证配置，recorder 永远保持八通道输入，不得在替换资源、同步 ROBOTEVT/其他项目配置、或创建新 demo 时改成 2 麦/2 通道。除非用户明确要求修改 recorder，否则只同步资源路径和 env，不改 recorder。

推荐 x86 recorder 基线：

```json
"recorder": {
    "mode": "external",
    "devName": "hw:1,0",
    "channels": 8,
    "sampleBits": 16,
    "sampleRate": 16000,
    "micChansNum": 4,
    "refChansNum": 1,
    "cachePcm": "false",
    "channel_mask": "12347"
}
```

关键点：
- `channels=8` 是 x86 实验的 ALSA 输入通道数，不能降成 2；降成 2 会导致实验音频布局不匹配，可能引发内存踩踏。
- 替换唤醒资源、sspe 资源、vad 资源时，只改对应 `*BinPath` / `env` / 唤醒词描述字段。
- 从板端配置或其他项目拷贝 app_config 时，必须单独检查 `app_config_x86.json` 的 recorder 是否仍为八通道基线。

### 配置一致性

更新 pot.json 时，参考相邻已有项目条目的字段结构，禁止凭空创建新字段。

### wakeup_words_conf 完整性与容量

- 替换唤醒资源或 `env` 时，保留原有 `wakeup_words_conf` 中仍适用的业务字段，例如 `wakeupWord`、`greeting`、`subsets`、`type`、`custom` 和 `net`；不得为了缩短配置而擅自删除字段。确需删除时，必须先说明行为影响并取得用户确认。
- 容量按 JSON 外层解析后的字符串计算 UTF-8 实际字节数，并额外预留结尾 `\0`；不能用字符数、配置文件转义后的文本长度或“比旧配置短”代替边界检查。
- 配置超过现有容量时，先用 `rg` 检查该字段的定义、复制点和消费/拼装缓冲区，再选择影响最小的容量调整；不得通过静默截断或遗漏业务字段规避溢出。
- 收尾时逐项核对 `env` 中 `words/thresh/thresh_high/thresh_low/major/custom/net` 的数量和顺序与 `wakeup_words_conf` 一致，并确认板端与 x86 配置按需求同步。

---

## changelog 规范

每次替换、新增项目、资源名变化、配置调整、源码兼容改动后必须更新 `changelogs/{PROJECT_NAME}.changelog.md`：

1. 在文件顶部新增版本条目，标题使用交付版本而不是 SDK 版本，格式：`## [v{delivery_version}] - {date}`
2. 记录更改内容和**详细改动文件列表**
3. **详细改动必须列出具体文件**（参考智元精灵 AGIBOT_GENIE 格式）：
   - SDK .so 文件用通配符：`./libs/duiplus_{id}/{platform_subdir}/*.so`
   - **SDK 头文件**：替换 SDK 时 `duiPlus.h` 也会更新，必须单独列出 `./libs/duiplus_{id}/{platform_subdir}/duiPlus.h`
   - `sspe.map`、`symtab.txt` 等 SDK 辅助文件统一忽略，不进入交付包、manifest 或 changelog
   - 资源文件逐个列出：`./res/{filename}.bin`
   - 源码文件逐个列出：`./src/{filename}.c`
   - 配置文件若被修改则列出：`./res/app_config.json`、`./res/app_config_{platform}.json` 等
   - **只列板端文件**，不列 x86 文件（x86 是内部验证用）。仅当项目只有 x86 时才写入
4. **版本信息必须完整**：`### 版本信息` 下第一条必须显式写 `- 交付版本: {delivery_version}`，不能只在标题或 `pot.json` 中体现；再列出当前所有资源（包括未变更的），如 SDK 版本、信号处理、VAD、唤醒词等
5. 主动向用户索取**需求单链接**和**说明信息**；若更新了 SDK，还需要主动索取 **SDK 来源链接**。用户暂时没有或未提供时，先写“待补充”，不得因此跳过 changelog
6. 格式参考已有条目保持一致
7. **最终核对**：提交最终回复前，必须用 `rg`/`find` 核对 changelog 中列出的资源文件名、SDK 目录、app_config 引用与磁盘最终状态一致；若过程中改过资源名或方案，必须重写为最新状态
8. **交付版本三方一致性检查**：最终核对 `pot.json` 的 `release_version`、changelog 顶部标题 `## [v{delivery_version}]`、顶部条目中的 `- 交付版本: {delivery_version}` 三者完全一致；缺少任意一处都不能收尾

```bash
delivery=$(jq -r --arg NAME "$PROJECT_NAME" '.[] | select(.name == $NAME) | .option.release_version' build/scripts/pot.json)
top_entry=$(sed -n '1,/^---------------------------------------$/p' "changelogs/${PROJECT_NAME}.changelog.md")
grep -Fq "## [v${delivery}]" <<< "$top_entry"
grep -Fxq -- "- 交付版本: ${delivery}" <<< "$top_entry"
```

**详细改动示例**（参考 AGIBOT_GENIE）：

```markdown
### 更改
- 更新 duiplus sdk 优化首字截断问题
- 详细改动：
    - ./libs/duiplus_90/rk3588_genie/*.so
    - ./libs/duiplus_90/rk3588_genie/duiPlus.h
```

```markdown
### 更改
- 更新sspe以及wakeup资源-解决高噪声唤醒率低问题
- 更新duiplus_sdk相关库内容
- 详细改动：
    - ./libs/duiplus_92/rk3588_genie/*.so
    - ./libs/duiplus_92/rk3588_genie/duiPlus.h
    - ./res/sspe_nnaec-ucann-ma-wnr-wkp_60_ch5-mic4-ref1_v2.0.0.175.bin
    - ./res/wkp_aihome_jiqiren_zhiyuan_20260519_v2.0.bin
```

```markdown
### 更改
- 更新duiPlus sdk支持双vad方案优化识别效果
- 详细改动:
    - ./libs/duiplus/duiplus_48/rk3588/*.so
    - ./include/duiplus.h
    - ./res/app_config_rk3588.json
    - ./res/sspe_aec_ucann_wkp_60_ch5_mic4_ref1_v2.0.0.160.bin
```

---

## 新增项目

当用户要求新增一个 demo 项目时，需完成以下步骤：

### 信息收集

向用户确认：
- 项目名称（pot.json `name` 字段，如 `GAUSIUM`）
- SDK 包目录（用于解析 solution_id、platform、version）
- 目标硬件平台（如 RK3588）
- 示例源文件选择（`duiplus_dds.c` / `duiplus_sspe_asr.c` / `duiplus_lite.c`）
- assets 目录名（`repo/assets/{customer}/{model}/`）

### 执行步骤

1. **拷贝 SDK 库** — 创建 `repo/libs/duiplus/duiplus_{id}/{platform_subdir}/`，拷贝 .so 和 duiPlus.h
2. **补充 libasound.so** — 从已有项目拷贝到 rk3588 目录（x86 用系统库，不需要）
3. **创建 app_config** — 在 `repo/assets/{customer}/{model}/` 下创建 `app_config_rk3588.json` 和 `app_config_x86.json`
4. **更新 pot.json** — 新增项目条目（含 manifest）
5. **更新 aimakefile** — 新增构建块
6. **更新 project_id_list** — 追加 `{name}-{中文描述}`
7. **创建 changelog** — 按初始版本格式创建
8. **源码兼容性检查** — 若新 SDK 缺少某些宏定义，给 `duiplus_dds.c` 等共享源文件加 `#ifdef` 守卫
9. **x86 编译验证** — 切换 x86 编译，通过后恢复板端配置

### 示例源文件与 CFLAGS 对应关系

| 源文件 | 典型 CFLAGS | LDFLAGS 额外项 |
|---------|-------------|---------------|
| `src/dds/duiplus_dds.c` | `-DALSA -DAUTH_ONLINE -DDUIPLUS -DUSE_MAC -DPSEUDO_DUAL_TTS -DOFFLINE_FREE_TALK -DENABLE_WELCOM` | `-lpthread` |
| `src/misc/duiplus_sspe_asr.c` | `-DALSA -DAUTH_ONLINE -DDUIPLUS -DUSE_MAC` | `-lpthread` |
| `src/misc/duiplus_lite.c` | `-DALSA -DAUTH_ONLINE -DDUIPLUS -DUSE_MAC -DUSE_LITE_VAD -DUSE_WAKEUP` | `-lrt -lpthread` |

### ES7210 音频芯片配置

RK3588 + ES7210 项目（如 LIMX、GAUSIUM）的 recorder 配置：

```json
"recorder": {
    "mode": "external",
    "devName": "hw:0,0",
    "channels": 8,
    "sampleBits": 16,
    "sampleRate": 64000,
    "alsa_param_channels": 2,
    "micChansNum": 4,
    "refChansNum": 1,
    "cachePcm": "false",
    "channel_mask": "56783"
}
```

关键点：
- `channels=8`：ALSA 设备报告的通道数
- `alsa_param_channels=2`：ES7210 实际输出的 TDM 通道数
- `sampleRate=64000`：ES7210 PDM 采样率
- `channel_mask`：根据实际硬件布线调整

## 仓库音频链路与重采样约定

修改录音采样率、通道数、`channel_mask` 或增加重采样宏时，必须先按下面的完整链路检查，不能只看某个 feed 线程能否编译：

```text
设备/离线文件
  -> record_audio() 或 audio_io.c/read_offline()
  -> channel_mask 通道选择与 FIFO(record_write/kfifo_in)
  -> record_read() 按消费者请求的字节数取数据
  -> 各项目 feed_loop
  -> SSPE/ASR SDK
```

### 录音配置字段的实际职责

- `recorder.channels` 是当前代码使用的逻辑/重排输入通道数，也是 `channel_mask` 的排列基础；它不一定等于硬件实际打开的通道数。
- `recorder.alsa_param_channels` 是 ALSA/部分硬件接口实际设置和读取的通道数；配置缺省时由 `cfg_parser.c` 设置为 `recorder.channels`。
- `micChansNum + refChansNum` 是送入算法的输出通道数，简称 `real_channels`。它必须与 SSPE 资源的 mic/ref 拓扑一致。
- `channel_mask` 在当前 `recorder.c` 和 `audio_io.c/read_offline()` 中各自解析，使用 `atoi` 从末位反向拆数字；修改解析规则、支持前导零或空回采时，实时录音和离线路径必须同时修改并验证。
- `audio_io.c` 的 `arrange_channels()` 当前直接按 `new_order` 访问源通道，没有通用的越界保护；mask 中的通道编号必须落在实际源通道范围内。`channel_mask` 长度也必须等于 `micChansNum + refChansNum`。

ES7210 是一个特殊布局：通常 `channels=8` 表示重组后的逻辑帧，`alsa_param_channels=2` 才是 ALSA 实际读取的通道数；`ES7210` 宏下会先做帧重组，再做 `channel_mask` 选择。不能把普通 ALSA 项目的 `channels`/`alsa_param_channels` 经验直接套到 ES7210 或 SSD202。

### 字节数和采样率契约

每通道每毫秒的字节数应按下式计算：

```text
bytes_per_ms = sample_rate / 1000 * bytes_per_sample
buffer_bytes = duration_ms * channel_count * bytes_per_ms
```

代码中的固定系数 `32` 只代表 `16 kHz + S16` 的单通道每毫秒字节数，不能代表任意采样率或位宽。当前仓库仍有以下固定假设，改采样率时必须一起审查：

- `src/common/recorder.c/record_init()` 用 `interval * real_channels * 32` 设置 FIFO 容量、`streamin_buffer_size`，并用 `interval * orig_channels * 32` 设置原始流阈值。
- `src/common/audio_io.c/read_offline()` 用固定 `32` 计算离线原始块和选通道后的块；选通道时还会把固定 `local_streamin_size` 写入 FIFO，即使最后一次 `fread()` 实际读到的是短块。
- `src/common/recorder.c` 的非 ES7210 分支、`src/dds`、`src/misc`、`src/sspe`、`src/vad` 下多个消费者各自用 `interval * channels * 32` 申请并请求块。
- `record_read()` 通常会等待 FIFO 中达到调用者请求的完整字节数；生产者和消费者的单位不一致时，表现可能是长时间阻塞、尾部短读、节奏变慢或离线音频提前结束。
- `record_write()` 当前没有统一检查 `kfifo_in()` 的实际写入返回值；排查 FIFO 丢数据或容量不足时要把这点纳入检查。

实时路径和离线路径的 dump 位置也要区分：`dump_stream_orig()` 是设备原始数据，`dump_stream_in()` 在通道选择后写入 FIFO 前执行；如果重采样放在某个 feed_loop 中，现有 `streamin` dump 仍是重采样前数据，不能据此判断 SDK 收到的采样率。

### 重采样实现边界

- `src/mic-ft/mic_ft_test.c` 中的 `DST_LIB_RESAMPLERATE` 是 MIC_FT_PX30 专用路径，不是全仓库公共重采样实现。它使用 `src_new()`/`src_process()` 的有状态转换，阅读或抽取时要同时检查输入帧数、输出容量、`input_frames_used` 和实际生成字节数。
- `MAGICROBOT` 的 `USE_RESAMPLE` 只在 `src/misc/duiplus_lite.c` 的 feed_loop 中生效：它从 FIFO 取出已选通道的 S16 音频，再转换到 16 kHz 后喂 duiplus SDK。它不会自动修正 `recorder.c` 的 FIFO 容量、`read_offline()` 的块大小，也不会改变其他项目 feed_loop 的固定 `32` 假设。
- 有状态重采样器必须跨 feed 块复用；每次循环重新 `src_new()` 会破坏连续性。初始化失败、处理失败和退出释放必须分别处理，不能只在成功路径释放。
- 重采样前后的通道数必须明确：当前 MAGICROBOT 路径先由 recorder 选择 `mic+ref` 通道，再按该输出通道数重采样；改变通道选择顺序时要重新确认 `SRC_DATA.input_frames` 的计算。
- 真正支持非 16 kHz 的完整方案，要么在 recorder/FIFO 入口统一把数据规范化为 SDK 的 `16 kHz/S16/real_channels`，要么让 FIFO、离线灌音和所有消费者都使用明确的原始采样率单位；只在单个消费者后面重采样不能宣称全仓库支持。

### 重采样库与平台依赖

- `repo/libs/micft/px30/libresamplerate.so` 是 AArch64 库，不能用于 x86；必须用 `file`/`readelf -h` 检查架构后再配置链接。
- ARM 的 MAGICROBOT 路径当前使用 `repo/libs/micft/samplerate.h`、`-I ./libs/micft`、`-L./libs/micft/px30/ -lresamplerate`，并将该库和头文件列入 MAGICROBOT manifest；`-Wl,--allow-shlib-undefined` 是兼容 SDK/旧 sysroot 的链接选项，与重采样本身无关，不应当作为重采样必选项传播到其他项目。
- MAGICROBOT 的 Linux/x86 分支使用 `-lsamplerate`，但当前仓库没有 x86 `libsamplerate.so` 随包提供，且 Linux 分支需要显式确认 `samplerate.h` 的 `-I` 来源。它目前依赖主机的 `libsamplerate` 开发包和运行时库；若要跨机器/交付运行，必须提供 ABI 匹配的 x86 库、加入 `-L`/rpath 和 manifest，或在文档中明确开发包依赖。
- `src/third/samplerate/` 是仓库内另一套采样率源码，不能因为目录存在就认为 MAGICROBOT 当前链接使用它；先看 `aimakefile` 的源文件和 `-l` 参数。
- `build/scripts/pack.sh` 按 manifest 从 `repo/` 复制文件到 `output/`，并在 output 目录内用相对 `-L`/rpath 编译。manifest 未列出的头文件或动态库不会因为源码目录存在而进入交付包。

### 音频改动检查表

涉及采样率或通道改动时，至少执行：

1. 搜索并审查 `record_init`、`record_audio`、`record_read`、`record_write`、`read_offline` 以及目标项目的全部 `record_read()` 消费者。
2. 分别计算设备原始块、通道选择块、FIFO 块和 SDK feed 块的字节数；确认每个 `malloc`、VLA、`kfifo_in/out` 和 `memcpy` 的长度一致。
3. 检查实时录音和离线灌音两条路径，特别是 WAV 头、短读、`record_write(NULL, 0)` 结束通知及 `feed_rate` 延时。
4. 对每个实际目标平台分别做编译；x86 和 ARM 的采样率库不能交叉使用。用 `file`/`readelf -d` 检查产物架构、SONAME、NEEDED 和运行时 rpath。
5. 通过 dump 文件和日志分别确认原始流、选通道流、重采样后送 SDK 的实际长度；不要只凭“编译成功”或 `streamin.pcm.dump` 判断重采样已生效。

### 初始版本 changelog 格式

参考 `AGIBOT_GENIE.changelog.md` 最早条目：

```markdown
# {中文名}-版本更新记录

## [v{delivery_version}] - {date}

### 更改
- 初始版本.
- 支持的特性：
    - {feature1}
    - {feature2}

### 版本信息
- 交付版本: {delivery_version}
- sdk版本: duiPlus_{id}_v{sdk_version}
- 信号处理: {sspe_resource}
- VAD: {vad_resource}
- 唤醒: {wakeup_resource}
- 本地识别: {asr_resource}

### 说明
- 需求单：{link}
- SDK来源：{link}
```

---

## 验证清单

```bash
# manifest ↔ 磁盘一致性
grep 'platform_subdir' build/scripts/pot.json | grep '.so' | sort
ls repo/libs/duiplus/duiplus_{id}/{platform_subdir}/*.so* | sed 's|.*/||' | sort

# sdk_version
grep sdk_version build/scripts/pot.json

# rpath
grep -A5 '项目名' aimakefile | grep rpath
```

通过标准：
- [ ] 目标目录 .so 文件数量与 manifest 条目数一致
- [ ] manifest 每条路径在磁盘上都存在
- [ ] 磁盘每个 .so 在 manifest 中都有条目
- [ ] sdk_version 已更新
- [ ] aimakefile rpath 正确
- [ ] app_config 中资源路径已同步
- [ ] changelog 已更新（含需求单、SDK来源）
- [ ] `pot.json.release_version`、changelog 顶部标题、`- 交付版本:` 三者一致
- [ ] x86 编译验证通过

### x86 编译验证

每次替换完成并确认资源一致性 OK 后，自动进行 x86 编译验证：

**流程：**

1. **切换到 x86** — 修改 pot.json 中项目的 `platform` 和 `aimake_type`：
   ```json
   "platform": "x86",
   "aimake_type": "linux"
   ```
2. **编译** — 执行：
   ```bash
   bash build/scripts/pack.sh <PROJECT_NAME>
   ```
3. **用户运行验证** — 等待用户确认运行结果
4. **恢复板端配置** — 用户说“恢复”后，将 pot.json 改回客户嵌入式平台：
   ```json
   "platform": "<原始平台>",
   "aimake_type": "<原始aimake_type>"
   ```

**注意：**
- 板端平台值从 aimakefile 中对应项目的 `ifeq ($(TARGET_PLATFORM), ...)` 条件确定
- 例如 LIMX: 板端为 `platform: "rk3588", aimake_type: "gcc-arm-9.2"`，x86 为 `platform: "x86", aimake_type: "linux"`
