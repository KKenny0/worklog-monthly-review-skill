# daily-note-monthly-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that processes long-running Daily Note files — splits them into monthly archives and generates structured monthly work summaries.

Designed for Obsidian Daily Note workflows, but works with any Markdown file that follows the heading structure convention (Year → Month → Date).

## What It Does

**Input:** A single `Daily Note.md` file containing months (or years) of work logs.

**Output (per month):**

| File | Description |
|------|-------------|
| `YYYY-MM.md` | Raw monthly archive — original content, unmodified |
| `YYYY-MM.summary.md` | Structured monthly summary — written by Claude based on template rules |

The summary extracts:
- Projects worked on and their active days
- Key accomplishments grouped by project and theme
- In-progress items and pending follow-ups
- Risk signals and next steps

## Quick Start

### Install

```bash
# Clone into your Claude Code skills directory
git clone https://github.com/KKenny0/worklog-monthly-review-skill.git \
  ~/.claude/skills/daily-note-monthly-review
```

### Use

In Claude Code, tell it:

> "Generate a monthly summary from my Daily Note at `path/to/Daily Note.md`"

Or more specifically:

> "Split `path/to/Daily Note.md` by month and generate summaries for 2026-03"

Claude will read the skill and follow the pipeline automatically.

## Daily Note Format

The skill expects your Daily Note to follow this heading structure:

```markdown
# 2026 年

## 2026 年 3 月
### 2026.03.02
- [Project Name]
	- {Module Name}
		- 今日进展：
			- 【能力升级】
				- [x] Completed task description
				- [ ] In-progress task description
```

Key conventions:
- **Project tags:** `- [Project Name]` — used to group work by project
- **Module tags:** `- {Module Name}` — sub-grouping within a project
- **Category tags:** `【能力升级】` `【结构变更】` `【问题定位】` `【配置调整】` `【文档优化】` `【阶段总结】` `【阶段冻结】`
- **Task status:** `[x]` completed, `[ ]` in-progress
- **Code changes:** Optional `(+N/-N 行)` annotation on tasks

See [`reference/daily-note-format.md`](reference/daily-note-format.md) for the full format specification.

## How It Works

```
Daily Note.md
    │
    ▼
┌──────────────────────────┐
│  Step 1: Read & Validate │  Check format, encoding, heading structure
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  Step 2: Split by Month  │  scripts/split_daily_note.py → YYYY-MM.md
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  Step 3: Extract Signals │  scripts/extract_worklog_signals.py → YYYY-MM.signals.json
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  Step 4: Build Summary   │  Claude reads archive + template → YYYY-MM.summary.md
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  Step 5: Print Summary   │  JSON output with projects, topics, warnings
└──────────────────────────┘
```

Steps 2-3 use deterministic Python scripts. Step 4 is where Claude reads the original archive and the summary template, then writes the monthly summary directly — no rigid templates, but guided by evidence-based rules.

## Design Principles

- **Facts first:** Every claim in the summary traces back to an original entry. No fabrication.
- **Inductive, not exhaustive:** Related tasks are grouped into theme paragraphs, not listed one by one.
- **Original untouched:** The monthly archive preserves the original Markdown exactly.
- **Summary ≠ report:** This skill produces factual summaries, not performance reviews or polished reports. That's a different layer.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `summary_mode` | `project_focused` | `light` / `project_focused` / `engineering_review` |
| `evidence_mode` | `strict` | `strict` (every claim needs source) / `best_effort` |
| `month_filter` | `null` | Process only a specific month, e.g. `"2026-03"` |
| `project_filters` | `[]` | Include only specified projects |
| `overwrite_policy` | `overwrite` | `overwrite` / `append` / `skip_existing` |

## Repository Structure

```
daily-note-monthly-review/
├── SKILL.md                          # Skill definition and workflow
├── scripts/
│   ├── split_daily_note.py           # Split Daily Note by month
│   ├── extract_worklog_signals.py    # Extract structured signals from archive
│   └── build_monthly_review.py       # Build skeleton JSON from signals
└── reference/
    ├── daily-note-format.md          # Daily Note format specification
    ├── worklog-summary-template.md   # Summary template and writing rules
    ├── project-tagging-guide.md      # Project classification methodology
    └── output-examples.md            # Input/output examples
```

## License

MIT
