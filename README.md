# daily-note-monthly-review

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that processes long-running Daily Note files — splits them into monthly archives and generates structured monthly work summaries.

Designed for Obsidian Daily Note workflows, but works with any Markdown file that follows the heading structure convention (Year → Month → Date).

## What It Does

**Input:** A single `Daily Note.md` file containing months (or years) of work logs.

**Output (per month):**

| File | Description |
|------|-------------|
| `YYYY-MM.md` | Raw monthly archive — original content, unmodified |
| `YYYY-MM.summary.md` | Structured monthly summary — written by Claude in narrative style |

The summary extracts:
- Projects worked on and their active days
- Work category distribution (能力升级/结构变更/问题定位/etc.)
- Work rhythm analysis across the month
- Key accomplishments grouped by project and theme
- Risks and next steps for handoff

## Quick Start

### Install

```bash
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
│  Step 4: Build Summary   │  scripts/build_monthly_review.py → YYYY-MM.skeleton.json
│                          │  Claude reads archive + template → YYYY-MM.summary.md
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  Step 5: Print Summary   │  JSON output with projects, topics, warnings
└──────────────────────────┘
```

Steps 2-4a use deterministic Python scripts. Step 4b is where Claude reads the skeleton data and the summary template, then writes the monthly summary in narrative style.

## Summary Output Style

The summary is written in **narrative paragraphs** (not bullet lists), following these principles:

- **Facts first:** Every claim traces back to an original entry. No fabrication.
- **Selective:** Only 2-3 core themes per project; routine work merged into one sentence.
- **Rhythm-aware:** The overview captures work phases (e.g. "early month focused on X, shifted to Y mid-month").
- **Quantitative:** Category distribution table and performance metrics when available.
- **Structured sections:** Overview → Work Distribution → Main Threads → Project Narratives → Risks → Next Steps → Data Notes.

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
    └── project-tagging-guide.md      # Project classification methodology
```

## Related

- [git-daily-note-updater-skill](https://github.com/KKenny0/git-daily-note-updater-skill) — Generate or update Daily Note entries from git commit history with diff analysis. Use it to fill in daily notes, then use this skill to produce monthly summaries.

## License

MIT
