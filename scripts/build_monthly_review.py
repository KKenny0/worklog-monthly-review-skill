#!/usr/bin/env python3
"""
build_monthly_review.py - 构建月度总结骨架

职责：
- 读取信号 JSON（extract_worklog_signals.py 的输出）
- 按项目归并条目
- 统计已完成/未完成事项
- 收集风险项和下一步信号
- 输出结构化总结骨架 JSON（供 Claude 生成 summary.md 使用）

不做：
- 不做语言润色（交给 Claude）
- 不做推理性总结（交给 Claude）
- 不做 Markdown 渲染（交给 Claude）
- 不做脑补

用法：
    python build_monthly_review.py <signals_file> <output_dir>
           [--summary-mode project_focused] [--evidence-mode strict]
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict


# 已知真实项目列表（用于区分误检测）
REAL_PROJECTS = {'AI 漫剧生成', '短剧成片', '专利'}


def group_by_project(entries):
    """按项目归并日志条目。"""
    project_entries = defaultdict(list)
    unassigned = []

    for entry in entries:
        if entry.get('projects'):
            for project in entry['projects']:
                project_entries[project].append(entry)
        else:
            unassigned.append(entry)

    return dict(project_entries), unassigned


def collect_completed_items(project_entries):
    """收集各项目的已完成事项。"""
    result = {}
    for project, entries in project_entries.items():
        items = []
        for entry in entries:
            for task in entry.get('completed_tasks', []):
                items.append({
                    'date': entry['date'],
                    'task': task,
                })
        result[project] = items
    return result


def collect_incomplete_items(project_entries):
    """收集各项目的未完成/进行中事项。"""
    result = {}
    for project, entries in project_entries.items():
        items = []
        for entry in entries:
            for task in entry.get('incomplete_tasks', []):
                items.append({
                    'date': entry['date'],
                    'task': task,
                })
            for signal in entry.get('status_signals', []):
                if signal in {'调整中', '优化中', '联调中', '测试中', '迭代中'}:
                    items.append({
                        'date': entry['date'],
                        'task': f"[进行中信号] {signal}",
                    })
        result[project] = items
    return result


def collect_risks(entries):
    """收集所有风险信号。"""
    risks = []
    for entry in entries:
        for signal in entry.get('risk_signals', []):
            risks.append({
                'date': entry['date'],
                'signal': signal,
                'projects': entry.get('projects', []),
            })
    return risks


def collect_next_actions(entries):
    """收集所有下一步信号。"""
    actions = []
    for entry in entries:
        for signal in entry.get('next_action_signals', []):
            actions.append({
                'date': entry['date'],
                'signal': signal,
                'projects': entry.get('projects', []),
            })
    return actions


def identify_main_threads(project_entries, high_freq_topics):
    """
    识别本月主线。
    基于项目跨度天数和高频主题，按活跃度排序。
    """
    threads = []
    for project, entries in project_entries.items():
        active_days = len(set(e['date'] for e in entries))
        categories = []
        for e in entries:
            categories.extend(e.get('categories', []))
        top_categories = [c for c, _ in Counter(categories).most_common(3)]

        threads.append({
            'project': project,
            'active_days': active_days,
            'top_categories': top_categories,
        })

    threads.sort(key=lambda t: t['active_days'], reverse=True)
    return threads


def build_review_skeleton(signals, summary_mode='project_focused', evidence_mode='strict'):
    """
    构建月度总结骨架。

    返回一个 dict，包含结构化的总结数据，供 Claude 生成 summary.md。
    """
    entries = signals.get('entries', [])
    month = signals.get('month', 'unknown')
    high_freq = signals.get('high_frequency_topics', [])

    # 按项目归并
    project_entries, unassigned = group_by_project(entries)

    # 收集各维度数据
    completed = collect_completed_items(project_entries)
    incomplete = collect_incomplete_items(project_entries)
    risks = collect_risks(entries)
    next_actions = collect_next_actions(entries)
    main_threads = identify_main_threads(project_entries, high_freq)

    # 统计
    total_completed = sum(len(items) for items in completed.values())
    total_incomplete = sum(len(items) for items in incomplete.values())

    skeleton = {
        'month': month,
        'summary_mode': summary_mode,
        'evidence_mode': evidence_mode,
        'real_projects': sorted(REAL_PROJECTS),
        'statistics': {
            'total_days': signals.get('total_days', 0),
            'total_projects': len(project_entries),
            'total_completed_tasks': total_completed,
            'total_incomplete_tasks': total_incomplete,
            'total_risk_signals': len(risks),
            'total_next_action_signals': len(next_actions),
        },
        'main_threads': main_threads,
        'high_frequency_topics': high_freq[:15],
        'by_project': {},
        'risks': risks,
        'next_actions': next_actions,
        'unassigned_entries_count': len(unassigned),
        'warnings': [],
    }

    # 按项目组织详细数据
    for project in project_entries:
        skeleton['by_project'][project] = {
            'completed_items': completed.get(project, []),
            'incomplete_items': incomplete.get(project, []),
            'active_days': len(set(e['date'] for e in project_entries[project])),
            'is_real_project': project in REAL_PROJECTS,
        }

    if summary_mode == 'engineering_review':
        skeleton['engineering_details'] = build_engineering_details(entries, project_entries)

    if unassigned:
        skeleton['warnings'].append(
            f"有 {len(unassigned)} 条日志条目未归属到任何项目标签"
        )
    if total_completed == 0:
        skeleton['warnings'].append("本月未检测到明确的已完成任务标记")
    if not high_freq:
        skeleton['warnings'].append("未能提取到高频主题关键词")

    return skeleton


def build_engineering_details(entries, project_entries):
    """构建 engineering_review 模式的额外详情。"""
    details = {
        'category_distribution': {},
        'daily_intensity': {},
    }

    all_categories = []
    for entry in entries:
        all_categories.extend(entry.get('categories', []))
    details['category_distribution'] = dict(Counter(all_categories))

    for entry in entries:
        date = entry['date']
        completed = len(entry.get('completed_tasks', []))
        incomplete = len(entry.get('incomplete_tasks', []))
        details['daily_intensity'][date] = completed + incomplete

    return details


def main():
    parser = argparse.ArgumentParser(description='构建月度总结骨架')
    parser.add_argument('signals_file', help='信号 JSON 文件路径')
    parser.add_argument('output_dir', help='输出目录路径')
    parser.add_argument('--summary-mode', default='project_focused',
                        choices=['light', 'project_focused', 'engineering_review'],
                        help='总结模式 (默认: project_focused)')
    parser.add_argument('--evidence-mode', default='strict',
                        choices=['strict', 'best_effort'],
                        help='证据模式 (默认: strict)')

    args = parser.parse_args()

    if not os.path.isfile(args.signals_file):
        print(f"错误：信号文件不存在 - {args.signals_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.signals_file, 'r', encoding='utf-8') as f:
        signals = json.load(f)

    skeleton = build_review_skeleton(signals, args.summary_mode, args.evidence_mode)

    # 保存骨架 JSON
    month = skeleton['month']
    os.makedirs(args.output_dir, exist_ok=True)
    skeleton_path = os.path.join(args.output_dir, f"{month}.skeleton.json")
    with open(skeleton_path, 'w', encoding='utf-8') as f:
        json.dump(skeleton, f, ensure_ascii=False, indent=2)

    print(f"骨架数据已保存：{skeleton_path}")
    stats = skeleton['statistics']
    print(f"统计：{stats['total_days']} 工作日 | {stats['total_projects']} 项目 | "
          f"{stats['total_completed_tasks']} 已完成 | {stats['total_incomplete_tasks']} 进行中")
    return skeleton


if __name__ == '__main__':
    main()
