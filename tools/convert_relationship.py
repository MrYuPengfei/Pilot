"""按外键拼装关系表（rel-*.csv）（已停用，v5.0 起不再保留任何特定游戏的数据源）。

历史上本脚本按各实体表的外键拼出 11 类关系表（角色↔食物↔材料、
武器↔突破材料、遗物↔实例等），产物是 ``data/csv`` 下的关系表。
其数据源涉及**未获授权的第三方版权素材**，与本项目当前的闭源许可声明不相容，
故在此版本中移除其实现。

⚠️ 该脚本此前还有两处问题，一并说明以免有人照抄：

1. 输入路径硬编码为 ``../../rec_intention/kg_data``——那个目录早已不在本仓库内，
   脚本**根本无法运行**；
2. 依赖 ``pandas``，而项目运行时依赖只有 PySide6 + pygame-ce，pandas 并不在其中。

关系表的现役构建方式是**直接编辑 CSV**，再由 ``kg_store`` 导入::

    data/csv-edu/rel-*.csv ──[tools/build_databases.py]──▶ kg.db

关系表的三列约定：``名称A, 关系名, 名称B``；引用的是**中文名**，
导入时端点解析会同时匹配 ``name`` 与 ``name_cn``（见 ``kg_store._import_endpoint``）。
"""

import os
import sys

#: 关系表 CSV 目录，与 ``tools/build_databases.py`` 的 CSV_DIR 保持一致。
KG_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'csv-edu')


def main():
    print(__doc__.strip())
    print('\n如需新增关系：直接编辑 CSV 后运行'
          ' python tools/build_databases.py --only kg --force')
    return 0


if __name__ == '__main__':
    sys.exit(main())
