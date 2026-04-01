#!/usr/bin/env python3
"""
extract_worklog_signals.py - 从月度归档中提取工作信号

职责：
- 读取月度归档文件 (YYYY-MM.md)
- 识别日期块、项目标签、模块标签、类别标签、任务状态
- 提取高频关键词、风险词、下一步信号
- 输出结构化 JSON 中间层

不做：
- 不做总结和归纳
- 不做推理性归类
- 不做内容改写

用法：
    python extract_worklog_signals.py <input_file> <output_file> [--summary-mode project_focused]
"""

import argparse
import json
import os
import re
import sys
from collections import Counter


# --- 识别正则 ---
RE_DATE = re.compile(r'^###\s*(\d{4})\.(\d{2})\.(\d{2})')
# 项目标签：- [项目名]，排除 [x] 和 [ ] 任务标记
RE_PROJECT = re.compile(r'^-\s*\[([^\]]+)\]')
RE_MODULE = re.compile(r'^\t-\s*\{([^}]+)\}')
RE_CATEGORY = re.compile(r'【([^】]+)】')
RE_TASK_DONE = re.compile(r'^\s*-\s*\[x\]')
RE_TASK_TODO = re.compile(r'^\s*-\s*\[\s*\]')

# --- 信号词库 ---
STATUS_COMPLETE = frozenset([
    '完成', '已完成', '已接入', '已验证', '已修复', '已落地', '交付', '上线',
])
STATUS_IN_PROGRESS = frozenset([
    '调整中', '优化中', '联调中', '测试中', '迭代中', '开发中', '重构中',
])
RISK_WORDS = frozenset([
    '风险', '问题', '阻塞', '不稳定', '兼容性', '待确认', '未验证', '异常', '崩溃', '死锁',
])
NEXT_ACTION_WORDS = frozenset([
    '下一步', '后续', '待补', '计划', '准备', '需要继续', '待开工',
])

# --- 已知的有效工作类别 ---
VALID_CATEGORIES = frozenset([
    '能力升级', '结构变更', '问题定位', '配置调整', '文档优化', '阶段总结', '阶段冻结',
])

# --- 常见无意义词过滤 ---
STOP_WORDS = frozenset([
    '的', '了', '在', '是', '和', '与', '或', '等', '到', '为', '对', '从',
    '将', '可', '被', '让', '用', '以', '及', '其', '该', '这', '那',
    '中', '上', '下', '内', '外', '前', '后', '之', '时', '里',
    '一', '个', '不', '有', '无', '也', '都', '还', '会', '能',
    '已', '新', '多', '更', '最', '所', '如', '而', '但', '使',
    '行', '点', '做', '加', '含', '项', '类', '组', '批', '套',
    # Daily Note 结构短语
    '今日进展', '当前应用', '新增', '支持', '移除',
    '确保', '添加', '优化', '使用', '增强', '实现', '更新',
    '修复', '改进', '集成', '引入', '统一', '规范化',
    '提升', '简化', '明确', '强制', '完善', '重构',
])


def extract_project(line):
    """从 `- [项目名]` 格式中提取项目名，排除 [x] 和 [ ] 任务标记。"""
    m = RE_PROJECT.match(line.strip())
    if m:
        name = m.group(1).strip()
        # 排除任务标记：x, 空格, 纯空白
        if name and name not in ('x', 'X') and not re.match(r'^\s*$', m.group(1)):
            return name
    return None


def extract_module(line):
    """从 `\\t- {模块名}` 格式中提取模块名。"""
    m = RE_MODULE.match(line)
    return m.group(1) if m else None


def extract_categories(text):
    """从文本中提取所有 `【类别】` 标签，只保留已知有效类别。"""
    found = RE_CATEGORY.findall(text)
    return [c for c in found if c in VALID_CATEGORIES]


def extract_status_signals(text):
    """从文本中提取状态信号。"""
    signals = []
    for word in STATUS_COMPLETE:
        if word in text:
            signals.append(word)
    for word in STATUS_IN_PROGRESS:
        if word in text:
            signals.append(word)
    return signals


def extract_risk_signals(text):
    """从文本中提取风险信号。"""
    signals = []
    for word in RISK_WORDS:
        if word in text:
            signals.append(word)
    return signals


def extract_next_action_signals(text):
    """从文本中提取下一步信号。"""
    signals = []
    for word in NEXT_ACTION_WORDS:
        if word in text:
            signals.append(word)
    return signals


def extract_keywords(text, top_n=20):
    """
    从文本中提取高频关键词。
    使用简单的分词策略：按中文词和英文短语切分。
    """
    # 提取中文短语（2-6字）和英文短语
    cn_phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    en_phrases = re.findall(r'[A-Za-z][A-Za-z0-9_]+', text)

    # 过滤停用词和太短的词
    cn_filtered = [p for p in cn_phrases if p not in STOP_WORDS and len(p) >= 2]
    en_filtered = [p for p in en_phrases if len(p) >= 3]

    counter = Counter(cn_filtered + en_filtered)
    return [word for word, count in counter.most_common(top_n)]


def parse_monthly_file(filepath):
    """
    解析月度归档文件，提取结构化信号。

    返回：
        dict: 月度信号数据
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    month_key = os.path.basename(filepath).replace('.md', '')

    entries = []
    current_date = None
    current_entry = None

    # 全文文本，用于关键词提取
    all_text = []

    for line in lines:
        stripped = line.strip()

        # 检测日期标题
        date_match = RE_DATE.match(stripped)
        if date_match:
            # 保存上一个 entry
            if current_entry:
                current_entry['raw_text'] = '\n'.join(current_entry.pop('_lines', []))
                entries.append(current_entry)

            year, month, day = date_match.groups()
            current_date = f"{year}.{month}.{day}"
            current_entry = {
                'date': current_date,
                'projects': [],
                'modules': [],
                'categories': [],
                'completed_tasks': [],
                'incomplete_tasks': [],
                'status_signals': [],
                'risk_signals': [],
                'next_action_signals': [],
                'topics': [],
                '_lines': [line],  # 临时保存原始行
            }
            continue

        if current_entry is None:
            continue

        current_entry['_lines'].append(line)
        all_text.append(stripped)

        # 提取项目标签
        project = extract_project(stripped)
        if project:
            current_entry['projects'].append(project)

        # 提取模块标签
        module = extract_module(line)
        if module:
            current_entry['modules'].append(module)

        # 提取类别标签（只保留已知有效类别）
        categories = extract_categories(stripped)
        if categories:
            current_entry['categories'].extend(categories)

        # 检测任务完成状态
        if RE_TASK_DONE.match(stripped):
            # 提取任务描述（去掉 [x] 前缀）
            task_desc = re.sub(r'^\s*-\s*\[x\]\s*', '', stripped)
            if task_desc:
                current_entry['completed_tasks'].append(task_desc)
        elif RE_TASK_TODO.match(stripped):
            task_desc = re.sub(r'^\s*-\s*\[\s*\]\s*', '', stripped)
            if task_desc:
                current_entry['incomplete_tasks'].append(task_desc)

        # 提取各类信号
        current_entry['status_signals'].extend(extract_status_signals(stripped))
        current_entry['risk_signals'].extend(extract_risk_signals(stripped))
        current_entry['next_action_signals'].extend(extract_next_action_signals(stripped))

    # 保存最后一个 entry
    if current_entry:
        current_entry['raw_text'] = '\n'.join(current_entry.pop('_lines', []))
        entries.append(current_entry)

    # 去重信号
    for entry in entries:
        entry['status_signals'] = list(set(entry['status_signals']))
        entry['risk_signals'] = list(set(entry['risk_signals']))
        entry['next_action_signals'] = list(set(entry['next_action_signals']))
        entry['projects'] = list(dict.fromkeys(entry['projects']))  # 去重保序
        entry['modules'] = list(dict.fromkeys(entry['modules']))
        entry['categories'] = list(dict.fromkeys(entry['categories']))

    # 全局关键词提取
    all_text_str = '\n'.join(all_text)
    global_keywords = extract_keywords(all_text_str)

    # 全局项目汇总
    all_projects = list(dict.fromkeys(
        p for entry in entries for p in entry['projects']
    ))

    # 全局类别汇总
    all_categories = list(dict.fromkeys(
        c for entry in entries for c in entry['categories']
    ))

    return {
        'month': month_key,
        'total_days': len(entries),
        'projects_detected': all_projects,
        'categories_detected': all_categories,
        'high_frequency_topics': global_keywords,
        'entries': entries,
    }


def main():
    parser = argparse.ArgumentParser(description='从月度归档中提取工作信号')
    parser.add_argument('input_file', help='月度归档文件路径 (YYYY-MM.md)')
    parser.add_argument('output_file', help='输出 JSON 文件路径')
    parser.add_argument('--summary-mode', default='project_focused',
                        choices=['light', 'project_focused', 'engineering_review'],
                        help='总结模式 (默认: project_focused)')

    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        print(f"错误：输入文件不存在 - {args.input_file}", file=sys.stderr)
        sys.exit(1)

    result = parse_monthly_file(args.input_file)

    # 根据模式调整输出
    if args.summary_mode == 'light':
        # light 模式：只保留日期、项目、关键词
        result['entries'] = [
            {
                'date': e['date'],
                'projects': e['projects'],
                'topics': e.get('topics', []),
            }
            for e in result['entries']
        ]

    # 写出
    os.makedirs(os.path.dirname(args.output_file) or '.', exist_ok=True)
    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"信号提取完成：{result['month']}")
    print(f"  日期数：{result['total_days']}")
    print(f"  项目：{', '.join(result['projects_detected'])}")
    print(f"  类别：{', '.join(result['categories_detected'])}")
    print(f"  高频主题（Top 10）：{', '.join(result['high_frequency_topics'][:10])}")

    return result


if __name__ == '__main__':
    main()
