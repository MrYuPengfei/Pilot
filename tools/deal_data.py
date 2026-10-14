"""素材整理辅助（v5.0 起仅保留通用工具函数）。

历史上的下载逻辑针对特定游戏的第三方版权素材，与本项目当前的闭源许可声明
及第三方素材授权清单（见 ``CREDITS.md``）不相容，故在此版本中移除，
只保留与数据源无关的通用小工具。

素材获取方式改为：使用**已获授权**的素材包（CC0 / CC-BY 等），按
``tools/build_assets_db.py`` 文档里的目录约定放入，再用它打包进 ``assets.db``。
"""

import sys


def add_zero(name, num=4):
    """把文件名的数字部分左侧补零到 ``num`` 位。

    用于动画帧排序：``9.png`` → ``0009.png``、``12.png`` → ``0012.png``。
    补零后字典序才等于播放顺序，否则 ``10.png`` 会排在 ``2.png`` 前面。

    已经是 ``num`` 位（或更长）的名字原样返回——不截断，避免丢信息。
    """
    length = name.split('.')[0]
    if len(length) >= num:
        return name
    return '0' * (num - len(length)) + name


def main():
    print(__doc__.strip())
    print('\n保留的通用工具：add_zero(name, num=4) —— 动画帧名左侧补零。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
