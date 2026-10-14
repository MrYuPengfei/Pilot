# -*- coding:utf-8 -*-
"""知识图谱从 Neo4j 导出为 CSV（已停用，v5.0 起不再保留任何特定游戏的数据源）。

历史上本脚本从外部 Neo4j 实例读取图谱，按 12 类实体表（``label-*.csv``）与
11 类关系表（``rel-*.csv``）导出为 CSV，再由 ``kg_store.py`` 导入 ``kg.db``。
其数据源涉及**未获授权的第三方版权素材**，与本项目当前的闭源许可声明不相容，
故在此版本中移除其实现。

⚠️ 本脚本此前把一个外部 Neo4j 实例的地址与**明文口令**硬编码在源码里。
这类凭据一旦进过版本库就应视为已泄露，若该实例仍在线请务必改密；
此类配置不再以任何形式写入源码（应改从环境变量读取）。

知识图谱的现役构建链路是**纯 CSV → SQLite**，不依赖任何图数据库::

    data/csv-edu/*.csv ──[tools/build_databases.py]──▶ kg.db

新增图谱请直接编辑 CSV 后重新构建，或在管理面板「知识图谱」页可视化编辑。
"""

import sys

#: 图谱 CSV 输入目录，与 ``tools/build_databases.py`` 保持一致。
KG_CSV_DIR = 'data/csv-edu'


def main():
    print(__doc__.strip())
    print(f'\n如需重建图谱库：编辑 {KG_CSV_DIR} 下的 CSV 后运行'
          ' python tools/build_databases.py --only kg --force')
    return 0


if __name__ == '__main__':
    sys.exit(main())
