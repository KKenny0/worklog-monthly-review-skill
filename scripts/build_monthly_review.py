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


# 默认最少出现天数阈值：出现天数 >= 此值的项目视为真实项目
DEFAULT_REAL_PROJECT_MIN_DAYS = 2


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


def detect_real_projects(project_entries, min_days=2):
    """根据出现天数自动识别真实项目，过滤误检测（如 Markdown 链接）。

    Markdown 链接误检测的特征：项目名通常只在 1 天出现，
    且文本中包含 URL（括号开头）。
    """
    real = set()
    for project, entries in project_entries.items():
        active_days = len(set(e['date'] for e in entries))
        if active_days >= min_days:
            real.add(project)
    return sorted(real)


def collect_completed_items(project_entries):
    """收集各项目的已完成事项。"""
    result = {}
    for project, entries in project_entries.items():
        items = []
        for entry in entries:
            for task in entry.get('completed_tasks', []):
                task_text = task['task'] if isinstance(task, dict) else task
                task_details = task.get('details', []) if isinstance(task, dict) else []
                items.append({
                    'date': entry['date'],
                    'task': task_text,
                    'details': task_details,
                })
        result[project] = items
    return result


def collect_daily_focuses(entries):
    """收集各日期的当日焦点。"""
    focuses = []
    for entry in entries:
        focus = entry.get('daily_focus', '')
        if focus:
            focuses.append({
                'date': entry['date'],
                'focus': focus,
            })
    return focuses


def collect_incomplete_items(project_entries):
    """收集各项目的未完成/进行中事项。"""
    result = {}
    for project, entries in project_entries.items():
        items = []
        for entry in entries:
            for task in entry.get('incomplete_tasks', []):
                task_text = task['task'] if isinstance(task, dict) else task
                task_details = task.get('details', []) if isinstance(task, dict) else []
                items.append({
                    'date': entry['date'],
                    'task': task_text,
                    'details': task_details,
                })
            for signal in entry.get('status_signals', []):
                if signal in {'调整中', '优化中', '联调中', '测试中', '迭代中'}:
                    items.append({
                        'date': entry['date'],
                        'task': f"[进行中信号] {signal}",
                        'details': [],
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


def build_review_skeleton(signals, summary_mode='project_focused', evidence_mode='strict',
                        real_projects=None, real_project_min_days=DEFAULT_REAL_PROJECT_MIN_DAYS):
    """
    构建月度总结骨架。

    参数：
        signals: 信号 JSON 数据
        summary_mode: 总结模式
        evidence_mode: 证据模式
        real_projects: 手动指定的真实项目列表（None 则自动检测）
        real_project_min_days: 自动检测的最少出现天数阈值

    返回一个 dict，包含结构化的总结数据，供 Claude 生成 summary.md。
    """
    entries = signals.get('entries', [])
    month = signals.get('month', 'unknown')
    high_freq = signals.get('high_frequency_topics', [])

    # 按项目归并
    project_entries, unassigned = group_by_project(entries)

    # 识别真实项目：手动指定 或 自动检测
    if real_projects is not None:
        detected_real = sorted(real_projects)
    else:
        detected_real = detect_real_projects(project_entries, real_project_min_days)

    # 收集各维度数据
    completed = collect_completed_items(project_entries)
    incomplete = collect_incomplete_items(project_entries)
    risks = collect_risks(entries)
    next_actions = collect_next_actions(entries)
    main_threads = identify_main_threads(project_entries, high_freq)
    daily_focuses = collect_daily_focuses(entries)

    # 统计
    total_completed = sum(len(items) for items in completed.values())
    total_incomplete = sum(len(items) for items in incomplete.values())

    skeleton = {
        'month': month,
        'summary_mode': summary_mode,
        'evidence_mode': evidence_mode,
        'real_projects': detected_real,
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
        'daily_focuses': daily_focuses,
        'unassigned_entries_count': len(unassigned),
        'warnings': [],
    }

    # 按项目组织详细数据
    for project in project_entries:
        skeleton['by_project'][project] = {
            'completed_items': completed.get(project, []),
            'incomplete_items': incomplete.get(project, []),
            'active_days': len(set(e['date'] for e in project_entries[project])),
            'is_real_project': project in set(detected_real),
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
    parser.add_argument('--real-projects', nargs='*', default=None,
                        help='手动指定真实项目列表（空格分隔），默认自动检测')
    parser.add_argument('--real-project-min-days', type=int,
                        default=DEFAULT_REAL_PROJECT_MIN_DAYS,
                        help=f'自动检测真实项目的最少出现天数阈值 (默认: {DEFAULT_REAL_PROJECT_MIN_DAYS})')

    args = parser.parse_args()

    if not os.path.isfile(args.signals_file):
        print(f"错误：信号文件不存在 - {args.signals_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.signals_file, 'r', encoding='utf-8') as f:
        signals = json.load(f)

    skeleton = build_review_skeleton(
        signals, args.summary_mode, args.evidence_mode,
        real_projects=args.real_projects,
        real_project_min_days=args.real_project_min_days,
    )

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
