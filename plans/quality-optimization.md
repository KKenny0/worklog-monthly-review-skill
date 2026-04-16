# 月度总结产出质量优化 TODO

## P0（核心质量）

- [x] **P0-1**: 重写 `worklog-summary-template.md` 示例为叙事段落风格（替换当前的 `**主题名**：描述` 列表格式）
- [x] **P0-2**: 在 SKILL.md Step 4b 增加取舍规则：每项目最多 2-3 主题、代码行数阈值（净增 >300 / 净减 >200）、配置/文档/小修复合并
- [x] **P0-3**: `build_monthly_review.py` 所有模式（非仅 engineering_review）都输出 `category_distribution`

## P1（结构优化）

- [x] **P1-1**: 模板中分离"问题与风险"和"下月衔接"为独立章节（当前合并为"进行中与待跟进"）
- [x] **P1-2**: `build_monthly_review.py` 新增 `phase_detection`：按周分组检测工作重心转移

## P2（长度控制）

- [x] **P2-1**: 统一总结长度目标：SKILL.md 和 template 都改为 80-120 行
