---
name: daily-note-monthly-review
description: >
  处理长期维护的 Daily Note.md，按月份拆分为独立的月度工作日志文件，并基于当月原始记录生成面向回顾与沉淀的月度总结分析文件。
  适用于 Obsidian Daily Note 长期整理、Work Diary 月度归档、周报/月报/绩效素材的上游准备、项目阶段回顾的事实层整理。
  当用户提到"月度总结"、"月报"、"Daily Note 拆分"、"工作日志整理"、"月度回顾"、"按月拆分日报"、"生成本月工作总结"时使用此 Skill。
  也适用于用户要求从 Daily Note 中提炼项目进展、工作主线、阻塞风险等结构化信息的场景。
---

# daily-note-monthly-review

面向工作沉淀的月度日志处理 Skill。核心产物：

- 一份原始月度归档（不改原文）
- 一份结构化月度总结（由 Claude 撰写，事实优先，禁止脑补）
- 一份可被周报、绩效、复盘复用的事实层输入

## 设计原则

- **事实优先**：只从原始记录中提取和归纳，不虚构缺失信息
- **原文不动**：归档文件保留原始 Markdown，不做改写
- **总结与日志分离**：归档和总结是两个独立文件
- **结构化输出**：使用固定模板，便于二次消费
- **允许总结，禁止脑补**：可以把多条记录归纳为一个主题，但不得凭空生成不存在的"成果"或"结论"

## 触发条件

当用户需要以下任何操作时，使用此 Skill：

- 按月拆分 Daily Note.md
- 生成月度工作总结
- 整理工作日志
- 为周报/月报/绩效准备素材
- 回顾某月项目进展

## 输入契约

### 必需输入

| 参数 | 说明 |
|------|------|
| `input_file` | Daily Note.md 的路径，UTF-8 编码，Markdown 格式 |
| `output_dir` | 输出目录路径 |

Daily Note 需具备明确的标题层级结构（年 → 月 → 日期），具体格式约定参见 `reference/daily-note-format.md`。

### 可选参数

```yaml
summary_mode: project_focused    # light | project_focused | engineering_review
overwrite_policy: overwrite      # append | overwrite | skip_existing
month_filter: null               # 只处理指定月份，如 "2026-03"
project_filters: []              # 只保留特定项目视角
evidence_mode: strict            # strict | best_effort
```

**参数说明：**

- `summary_mode`：控制总结深度。`light` 只提炼主线和关键词；`project_focused`（默认）按项目归并，提炼重点事项；`engineering_review` 强化问题/方案/风险/验证结构
- `overwrite_policy`：已有文件时的处理策略。`overwrite`（默认）覆盖，`append` 追加，`skip_existing` 跳过
- `month_filter`：只处理指定月份，格式 `YYYY-MM`，`null` 表示处理所有月份
- `project_filters`：只保留指定项目的视角，如 `["项目A"]`，空列表表示不限
- `evidence_mode`：`strict`（默认）要求每条总结都有原文依据，`best_effort` 允许适度归纳

## 输出契约

### 1. 月度归档文件 `YYYY-MM.md`

- 保留原始 Markdown 内容，不改写
- 按原始日期顺序组织
- 不跨月重排

### 2. 月度总结分析文件 `YYYY-MM.summary.md`

- 由 Claude（而非脚本）基于骨架数据和模板撰写
- 使用 `reference/worklog-summary-template.md` 中定义的格式和规则
- 显式区分"事实"、"归纳"、"信息缺口"
- 不输出缺乏依据的判断

### 3. 执行摘要（终端输出）

```json
{
  "months_created": ["2026-03"],
  "months_updated": [],
  "summaries_created": ["2026-03.summary.md"],
  "summary_mode": "project_focused",
  "projects_detected": ["项目A", "项目B"],
  "high_frequency_topics": ["核心模块", "性能优化", "API集成"],
  "warnings": []
}
```

## 执行步骤

按以下顺序执行，每步完成后进入下一步。如果某步失败，向用户报告错误内容，不要跳过继续。

### Step 1：读取与预检

1. 确认 `input_file` 存在且可读
2. 检查编码（必须是 UTF-8）
3. 识别标题层级结构，确认至少存在月级别和日级别的标题
4. 如果格式不符合预期，提示用户检查 `reference/daily-note-format.md` 中的格式约定

**格式识别规则：**

```
年标题：  ^#\s*\d{4}\s*年
月标题：  ^##\s*\d{4}\s*年\s*\d{1,2}\s*月
日标题：  ^###\s*\d{4}\.\d{2}\.\d{2}
```

注意：年月标题中的"年"和"月"前后可能有空格（如 `2026 年 3 月`），正则需要兼容。

### Step 2：按月拆分归档

1. 运行 `scripts/split_daily_note.py`，传入 `input_file` 和 `output_dir`
2. 脚本解析年/月/日节点，将同月内容合并输出为 `YYYY-MM.md`
3. 按 `overwrite_policy` 处理已有文件
4. 如果指定了 `month_filter`，只输出该月
5. 检查脚本输出，确认生成的月度文件数量和内容正确

### Step 3：提取工作信号

1. 对每个需要生成总结的月份，运行 `scripts/extract_worklog_signals.py`
2. 脚本从月度归档中提取结构化信号：
   - 项目标签（`- [xxx]` 格式）
   - 模块标签（`- {xxx}` 格式）
   - 类别标签（`【能力升级】`、`【结构变更】`、`【问题定位】`等）
   - 完成状态（`[x]` 已完成 / `[ ]` 未完成）
   - 具体工作内容文本
3. 输出中间层 JSON 结构，供下一步使用
4. 将中间层 JSON 保存到 `output_dir` 下（文件名 `YYYY-MM.signals.json`），方便调试和复用

### Step 4：构建总结

分两步完成：先用脚本生成骨架 JSON，再由 Claude 撰写总结。

#### 4a：脚本生成骨架 JSON

1. 运行 `scripts/build_monthly_review.py`，传入信号 JSON 路径和输出目录路径
2. 脚本完成确定性工作：
   - 按项目归并条目
   - 统计已完成/未完成事项
   - 收集高频关键词
   - 识别风险词和下一步信号
   - 将 `real_projects` 列表加入骨架 JSON
3. 输出结构化骨架 JSON（`YYYY-MM.skeleton.json`）

#### 4b：Claude 撰写总结

读取 `reference/worklog-summary-template.md` 模板、读取 `YYYY-MM.skeleton.json` 骨架数据、读取原始月度归档 `YYYY-MM.md`。

然后按模板格式撰写 `YYYY-MM.summary.md`，写入到与月度归档相同的目录。

**重要约束：**

- `evidence_mode=strict` 时，每条总结必须能在原文中找到对应条目
- 不要把"优化中"说成"已完成"
- 不要把多条独立的小修复包装成"重大成果"
- 如果某个项目在当月只有零星记录，如实说明"记录较少"，不要强行展开
- 同一任务跨多个项目时，只在活跃天数最多的项目下列出，避免重复
- 已完成事项按类别分组（能力升级/结构变更/问题定位/配置调整/文档优化），不按平铺列表
- 保留关键数据的代码变更量信息（如 `+160/-2 行`），它们能快速反映工作规模
- 误检测项目（不在 `real_projects` 列表中的）在"本月主线"中标注，但不展开详细事项
- 总结总长度控制在 300 行以内

### Step 5：输出执行摘要

在终端输出结构化执行摘要（JSON 格式），包含：

- 处理的月份列表
- 生成的文件列表
- 检测到的项目列表
- 高频主题
- 警告信息（如格式异常、归类模糊项等）

## 项目归类规则

项目通过 Daily Note 中的 `- [项目名]` 标签自动识别，不预设固定列表。Claude 从月度归档中扫描所有 `- [xxx]` 标签，汇总为本月项目清单。

核心原则：
- 以 `[项目名]` 标签为归类依据，不根据内容猜测
- 遇到未识别的标签，保留原始标签，在总结数据说明中提示
- Markdown 链接 `[文本](URL)` 不是项目标签，注意区分

详细归类规则参见 `reference/project-tagging-guide.md`。

## 工作类别识别

日志中的工作类别通过 `【xxx】` 格式标记：

| 类别 | 含义 |
|-----|------|
| `【能力升级】` | 新功能开发、功能增强 |
| `【结构变更】` | 重构、架构调整、模块拆分 |
| `【问题定位】` | Bug 修复、问题排查 |
| `【配置调整】` | 参数调整、配置优化 |
| `【文档优化】` | 文档更新、README |
| `【阶段总结】` | 阶段性总结 |
| `【阶段冻结】` | 功能冻结 |

## 状态信号识别

### 已完成信号

- 任务列表标记为 `[x]`
- 文本中出现：完成、已完成、已接入、已验证、已修复、已落地

### 进行中信号

- 任务列表标记为 `[ ]`
- 文本中出现：调整中、优化中、联调中、测试中、迭代中

### 风险信号

- 文本中出现：风险、问题、阻塞、不稳定、兼容性、待确认、未验证

### 下一步信号

- 文本中出现：下一步、后续、待补、计划、准备、需要继续

## 边界与非目标

此 Skill **不负责**：

- 改写原始 Daily Note
- 写汇报文案
- 生成绩效表述
- 判断工作价值高低
- 把零散记录包装成"成果"

此 Skill **只负责**：

- 拆分 → 归档 → 提炼 → 结构化输出

更上层的"周报风格化输出""绩效包装"应由其他 Skill 处理。

## 错误处理

1. **文件不存在**：报告路径，提示用户检查
2. **编码异常**：报告具体位置，建议用 UTF-8 重新保存
3. **标题层级不识别**：展示实际找到的标题层级，提示用户参考 `reference/daily-note-format.md` 调整
4. **某月无内容**：正常处理，生成空月度文件，在总结中标注"本月无记录"
5. **脚本执行失败**：报告完整错误信息，不要吞掉异常

## reference 文件说明

| 文件 | 何时读取 |
|-----|---------|
| `reference/daily-note-format.md` | 需要理解 Daily Note 格式约定时 |
| `reference/worklog-summary-template.md` | Claude 撰写总结时（必须读取） |
| `reference/project-tagging-guide.md` | 需要项目归类规则时 |
| `reference/output-examples.md` | 需要参考输入输出样例时 |
