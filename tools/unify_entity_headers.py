"""统一 data/csv-edu 的实体表表头为四列约定。

**为什么要统一**：实体表原本各用各的写法——``name``（英文）+
``label``（中文名）+ ``category``（领域）。同一个 ``label`` 列在不同来源里
语义完全不同，是导入器里那段「像类型键就用它、否则当中文名」猜测逻辑的根源。
统一成下面四列后，猜测可以彻底删掉：

===========  ==========================================================
列名          含义
===========  ==========================================================
``name``      **实体主键**（英文名；暂无官方译名时可为空，回退 ``name_cn``）
``name_cn``   中文名（作属性保存，供展示与中文搜索）
``label``     类型键（``ai`` / ``education`` / …），类型由它决定
``label_cn``  类型中文名（``AI领域`` / …），仅作展示
===========  ==========================================================

⚠️ **主键必须是 ``name`` 而不是 ``name_cn``**：中文名**不唯一**——
实测 csv-edu 有 11 组同中文名（``RLHF`` 与 ``reinforcement learning from
human feedback`` 共用「基于人类反馈的强化学习」）。拿中文名当主键会让同一概念
裂成多个实体，实测节点数 732→1392 翻倍、关系数 1063→784 骤降
（端点解析失败退化成桩）。英文名则稳定唯一。

关系表 ``rel-*.csv`` 引用的是**中文名**，故导入时端点解析会同时匹配
``name`` 与 ``name_cn``（见 ``kg_store._import_endpoint``）。

**改造规则**（幂等，可重复执行）::

    python tools/unify_entity_headers.py --check   # 只校验
    python tools/unify_entity_headers.py           # 就地改写

csv-edu ``label-*.csv``
    ``label`` → ``name_cn``（原 label 存的是中文名）；``category`` →
    ``label_cn``（原category 存的是领域中文名）；**新增** ``label``
    （类型键，从文件名 ``label-<type>.csv`` 取，如 ``ai``）。

⚠️ 保持**无 BOM**；行尾统一为 LF（原 csv-edu 为 CRLF，选影响面小的一边）。
"""

import argparse
import csv
import glob
import io
import os
import sys

#: 实体表 CSV 目录，与 ``tools/build_databases.py`` 的 CSV_DIR 保持一致。
EDU_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'csv-edu')

# 统一后的实体表列顺序。``name`` 在前：它是「英文名」这一主字段，
# 空值时导入器回退到 name_cn，故列不能省。
NODE_COLUMNS = ['name', 'name_cn', 'label', 'label_cn']


def _read(path):
    """读 CSV，返回 (行列表, 列名列表)。用 utf-8-sig 兼容有无 BOM。"""
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def _read_text(path):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def _render(columns, rows):
    """按列顺序渲染成 CSV 文本（LF 行尾、无 BOM）。

    ⚠️ 源文件行尾是 CRLF，脚本统一按 LF 输出：Python 的 csv 与 Excel 都能正确读 LF，
    而反向（改成 CRLF）对已是 LF 的文件是全文件 diff，故选影响面小的一边。
    """
    buf = io.StringIO(newline='')
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(columns)
    for r in rows:
        writer.writerow([r.get(c, '') for c in columns])
    return buf.getvalue()


def unify_edu(csv_dir=EDU_DIR, check_only=False):
    """csv-edu label-*.csv：label→name_cn、category→label_cn、新增 label。

    ⚠️ 源数据里 ``label`` 存的是**中文名**，而中文名在新约定里叫 ``name_cn``；
    类型键（``ai``）要从**文件名**取。

    🔴 **必须先判断是否已改造过**，否则第二次执行会把 ``name_cn`` 覆盖成
    类型键：改造后 ``label`` 列存的是 ``ai``，而本函数仍按「label 是中文名」
    去读它，于是 ``name_cn`` 变成 ``ai``、中文名丢失。
    判据是**列名已存在**（``name_cn``/``label_cn`` 是本次才引入的），
    而不是猜内容——猜内容在这种「值恰好合法」的情况下不可靠。
    """
    report = {'dir': csv_dir, 'files': 0, 'rows': 0, 'changed': 0,
              'skipped': 0}
    for path in sorted(glob.glob(os.path.join(csv_dir, 'label-*.csv'))):
        rows, fields = _read(path)
        if not rows:
            continue
        report['files'] += 1
        report['rows'] += len(rows)

        # 已改造过：列名齐备则原样跳过（只补可能缺的 label）
        if 'name_cn' in fields and 'label_cn' in fields:
            report['skipped'] += 1
            continue

        ntype = os.path.basename(path)[len('label-'):-len('.csv')]
        out = []
        for r in rows:
            new = {}
            for k, v in r.items():
                if k == 'name':
                    new['name'] = (v or '').strip()      # 本来就是英文名
                elif k == 'label':
                    new['name_cn'] = (v or '').strip()   # label 存的是中文名
                elif k == 'category':
                    new['label_cn'] = (v or '').strip()  # category 存的是领域
                else:
                    new[k] = v
            # 类型键：csv-edu 原本没有这一列，从文件名补
            new['label'] = ntype
            out.append(new)

        columns = NODE_COLUMNS + [c for c in fields
                                  if c not in ('name', 'label', 'category',
                                               'name_cn', 'label_cn')]
        columns = NODE_COLUMNS + [c for c in dict.fromkeys(columns)
                                  if c not in NODE_COLUMNS]
        payload = _render(columns, out)
        if _read_text(path) != payload:
            report['changed'] += 1
        if not check_only:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(payload)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description='统一实体表的表头为 name/name_cn/label/label_cn')
    ap.add_argument('--check', action='store_true', help='只校验，不写入')
    args = ap.parse_args(argv)

    verb = '待更新' if args.check else '已更新'
    rep = unify_edu(check_only=args.check)
    print('csv-edu：')
    print(f'  {rep["files"]} 个实体表 / {rep["rows"]} 行，{verb} {rep["changed"]} 个')
    print(f'  列：{", ".join(NODE_COLUMNS)} + 原有业务列')
    print()
    print('关系表 rel-*.csv 未改动（它们引用中文名，正是 name_cn）。')
    if not args.check:
        print('⚠️ name 列为空的实体导入时会回退到 name_cn，'
              '不影响导入与中文搜索。')
    return 0


if __name__ == '__main__':
    sys.exit(main())