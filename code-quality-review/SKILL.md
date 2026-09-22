---
name: code-quality-review
description: Extend Codex code review with repository-quality checks for reuse, solution extraction, versions, documentation, and comments, plus dui-apis-demo-linux duiPlus DDS customer-business separation compliance. Use when reviewing pull requests, branches, commits, or uncommitted changes, including requests such as 代码评审, review, 检查复用, 版本号, 文档, or 注释. Preserve the built-in /review correctness checks, report evidence-backed findings, and do not modify code. Do not use for implementation-only tasks or general code explanations without a change set.
---

# Review Code Quality

## Goal

在 Codex 内置 `/review` 的正确性、安全性、性能和回归检查之上，追加“复用与方案沉淀”、“版本号”、“文档覆盖”和“必要注释”四类质量检查；在 duiPlus DDS 相关变更中，再检查客户业务拆分方案符合性。

保持评审只读。只报告有具体证据、可定位且可行动的问题。

## Workflow

1. 确定变更范围。当技能由 `/review` 上下文启动时，沿用其已选择的基准分支、commit 或未提交变更；否则根据用户指定的 diff、分支、commit 或工作区确定范围。
2. 读取适用的 `AGENTS.md`、贡献指南、发布规则、版本规则和文档约定。以仓库明确规则为准。
3. 执行内置 review 的常规检查，再对本次变更执行下面的附加检查；若属于 duiPlus DDS 相关变更，还必须执行客户业务拆分方案检查。
4. 通过代码搜索、调用点、版本来源和文档入口验证每个候选问题。无法验证时，将其降级为待确认项，不得表述为已确认缺陷。
5. 输出优先级明确的 findings 和附加检查摘要。不为了填满报告而制造问题。

## Check Reuse And Solution Extraction

- 搜索仓库中已有的类、函数、模块、配置、资源、测试工具和相似业务流程，判断新代码是否重复实现已有能力。
- 比较语义和职责，不要仅因为代码形状相似就判定重复。
- 检查新增的通用能力是否被困在特定功能、页面或产品分支中，导致后续无法复用或不得不复制。
- 检查通用解决方案是否放入仓库约定的公共模块，并保留必要的用法入口、测试或示例，便于团队发现和复用。
- 仅当能指出具体的已有实现、重复片段或清晰的多处复用需求时才报告问题。在 finding 中同时引用变更位置和可复用的已有位置。
- 不要为一次性的简单逻辑强制创建抽象，也不要提出尚无第二个使用场景的推测性框架。
- 优先建议最小整合方案：复用已有入口、扩展既有抽象，或在已出现多个真实使用点时提取公共能力。

## Check Version Updates

- 识别仓库的真正版本来源和发布策略，例如构建配置、manifest、包元数据、版本文件、tag 规则或自动发布配置。
- 只有当仓库规则要求，或变更将产生新的可发布产物、对外 API 或兼容性影响时，才要求更新版本号。不要假定每个 commit 都必须升版。
- 检查主版本源与子模块、包、依赖锁定文件、构建常量、发布说明和用户可见版本信息是否一致。
- 根据仓库的语义化版本或内部版本策略，检查升版类型是否与破坏性变更、新功能或修复相匹配。
- 当无法从仓库证据确定是否应该升版时，在摘要中标记为“待确认”，不要直接报告“版本未更新”。

## Check Documentation Coverage

- 列出变更影响的用户可见行为，包括 API、CLI、配置、数据格式、部署流程、操作步骤、限制、故障处理和迁移要求。
- 检查 README、API 文档、配置参考、示例、changelog、迁移文档和运维手册中与该变更相关的入口。
- 逐项对照新增、修改或删除的对外行为，确认参数、默认值、示例、兼容性和升级步骤均已同步。
- 对纯内部重构、无用户可见影响的修复或仓库明确不要求文档的变更，标记为“不适用”，不要强制添加文档。
- 报告文档问题时，指明遗漏的具体行为、应更新的文档位置以及用户可能得到的错误认知。

## Check Necessary Comments

- 要求注释解释“为什么”，而不是重复代码已清楚表达的“做了什么”。
- 检查非显而易见的业务约束、不变式、协议细节、并发或时序要求、性能取舍、安全边界、兼容性 workaround 和看似多余但必须保留的逻辑是否有必要说明。
- 检查仓库规则要求的公开 API 文档注释是否完整，并检查现有注释是否因变更而过时、误导或与实现矛盾。
- 不要要求为自解释的代码、普通 getter/setter、直接的数据映射或简单控制流添加注释。
- 报告注释问题时，说明不补充或不更新注释将如何导致误用、回归或重复调查。

## Check duiPlus DDS Customer Business Separation

- 在 `dui-apis-demo-linux` 中，只要变更影响 `src/dds/duiplus_dds*.c`、`duiplus_core.h`、`duiplus_feature.h`、`src/dds/features/`、`src/dds/profiles/`，或这些文件对应的 `aimakefile`、`build/scripts/pot.json` 配置，就视为 duiPlus DDS 相关变更。
- 对此类变更，必须读取仓库内的 `repo/docs/duiplus/客户业务拆分方案.md`，将其作为方案规格逐项核对并引用具体章节。若文件缺失或当前仓库不是该方案的适用仓库，将状态标为“待确认”，说明缺失上下文。
- 检查 Core、Feature、Profile 的职责边界；客户名称、资源、常量、策略和命令不得回到 Core，客户参数和 Feature 组合应集中在 Profile，独立能力应优先复用或沉淀为职责单一的 Feature。
- 检查每个目标只链接一个 Profile、Feature 未处理的消息或事件返回 0、明确拦截才跳过 Core、初始化与逆序释放保持配对，并完整追踪回调、消息队列、播放停止和释放时序。
- 成对核对项目 `aimakefile` 块和 `pot.json` manifest 中的 Core、Feature、Profile 与公共头文件；有条件时执行目标工具链编译和发布包检查，确认未混入其他客户代码。无法执行时标为“待确认”，不要把未验证表述为失败。
- 迁移或新增客户需求时，检查是否保持原行为、删除旧 Core 路径，并避免新旧实现并存。报告 finding 时同时引用变更位置和方案章节，说明违反的职责或交付约束。

## Evidence And Severity

- 将文件和行号定位到最小相关变更范围。在支持行内评论的客户端中，将 finding 附着在最能说明问题的行上。
- 对每个 finding 说明触发条件、具体影响和最小修复方向。
- 仅将会导致发布错误、外部契约错误或明确高维护风险的附加规则问题标为 P1/P2。将局部可维护性问题标为 P3。不要因为它们是团队规则就虚高优先级。
- 如果问题仅是个人风格偏好、没有实际影响，或无法给出仓库证据，不要输出 finding。

## Output Format

先输出内置 review 格式的 findings，按优先级从高到低排列。每条使用下列结构：

```text
[P2] 简短、可执行的标题
位置：path/to/file:line
证据：已查看的变更、已有实现或仓库规则。
影响：问题在什么条件下发生，会造成什么后果。
建议：最小修复方向。
```

在 findings 后输出附加规则摘要：

```text
附加质量检查
- 复用与方案沉淀：通过 / 存在问题 / 待确认
- 版本号：通过 / 存在问题 / 待确认 / 不适用
- 文档覆盖：通过 / 存在问题 / 待确认 / 不适用
- 必要注释：通过 / 存在问题 / 待确认 / 不适用
- duiPlus DDS 客户业务拆分：通过 / 存在问题 / 待确认 / 不适用
```

为每个“存在问题”或“待确认”状态附一句证据或缺失的上下文。如果没有可行动的 finding，明确输出“未发现需要阻止合并的问题”，仍保留附加规则摘要。
