# -*- coding: utf-8 -*-
"""原素材采集爬虫（已停用，v5.0 起不再保留任何特定游戏的数据源）。

本脚本此前抓取某游戏官方资料站（``ys_obc``）的公开接口，采集图鉴素材与知识图谱。
该数据源涉及**未获授权的第三方版权素材**，与本项目当前的闭源许可声明
及第三方素材授权清单（见 ``CREDITS.md``）不相容，故在此版本中移除其实现。

素材与图谱的现役来源：

* **素材** —— 已获授权的第三方素材包（CC0 / CC-BY 等），按
  ``tools/build_assets_db.py`` 文档里的目录约定放入，再打包进 ``assets.db``；
* **图谱** —— ``data/csv-edu/*.csv``，纯 CSV → SQLite，见 ``tools/build_databases.py``。

两条链路都**不依赖任何爬虫**，也不访问任何游戏厂商的接口。
"""

import sys


def main():
    print(__doc__.strip())
    print('\n如需新增素材：放入已获授权的素材包后运行'
          ' python tools/build_assets_db.py 生成 assets.db。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
