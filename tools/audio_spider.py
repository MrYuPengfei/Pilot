"""素材批量下载辅助（已停用，v5.0 起不再保留任何特定游戏的数据源）。

历史上本脚本用于从第三方站点批量抓取角色语音，填入 ``music/<角色>/`` 目录。
该数据源涉及**未获授权的第三方版权素材**，与本项目当前的闭源许可声明
及第三方素材授权清单（见 ``CREDITS.md``）不相容，故在此版本中移除其实现。

素材获取方式改为：使用**已获授权**的素材包（CC0 / CC-BY 等），按
``music/<角色>/`` 与 ``music/<地区>/background.mp3`` 的目录约定放入后，
用 ``tools/build_assets_db.py`` 打包进 ``assets.db``。

⚠️ 目录约定本身就是语义（详见 ``tools/build_assets_db.py`` 的模块文档）：
``music/<角色>/闲聊*.mp3`` 是角色语音，``music/<地区>/background.mp3``
才是地区背景音乐，二者播放入口不同——**改名会改变素材语义**。
"""

import sys


def main():
    print(__doc__.strip())
    print('\n如需导入自己的素材：把已获授权的素材按上述目录约定放好后，'
          '运行 python tools/build_assets_db.py 生成 assets.db。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
