"""启动路径冒烟测试：保证打包后 exe 能真的起来。

🔴 **为什么需要这个文件**
打包产物与源码运行有两处关键差异，单元测试全都绕过了：

1. **导入路径**：源码跑时 ``sys.path[0]`` 是项目根，各模块能直接找到；
   PyInstaller 打包后 ``pilot.py`` 与 ``asset_importer.py`` 被摊平到 ``_internal/``，
   **任何拼写错误（如 ``import_assetsy``）只有打包后才会暴露**——
   源码运行时因为根本没执行到那行，同样「通过」。
2. **随包数据**：``res/help.html``、三个 ``.db`` 缺失时程序能起来，
   但帮助页空白 / 素材为空，属于「能跑但不对」，同样测不出来。

因此这里用**子进程起一个真实的 Python 解释器**跑 ``pilot.py``，
把 stdout+stderr 落盘后断言为空——不依赖 pytest 的同进程导入，
从而真正覆盖「从头执行」这条路径。
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'pilot.py'


def _run_offscreen(seconds=12):
    """离屏跑 pilot.py，返回 (输出文本, 退出码或None)。"""
    import tempfile
    log = Path(tempfile.gettempdir()) / 'pilot_smoke_test.log'
    if log.exists():
        log.unlink()
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', SDL_AUDIODRIVER='dummy')
    with open(log, 'wb') as f:
        p = subprocess.Popen([sys.executable, str(PILOT)], cwd=str(ROOT),
                             stdout=f, stderr=subprocess.STDOUT, env=env)
        try:
            code = p.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            # 托盘程序本就该常驻，超时属预期
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
            code = None
    return log.read_bytes().decode('utf-8', 'replace').strip(), code


@pytest.mark.skipif(not PILOT.is_file(), reason='pilot.py 不存在')
def test_pilot_starts_without_error():
    """启动 pilot.py 不应有任何输出。

    回归价值：曾出现 ``from asset_importer import import_assetsy``
    （函数名多打一个 y），309 个单测全绿、打包后 exe 一启动就 ImportError 退出——
    因为源码跑测试时那行根本不会被执行到。本测试是唯一能拦住它的网。
    """
    out, _code = _run_offscreen()
    assert out == '', f'启动有输出（应为空）：\n{out[:2000]}'


@pytest.mark.skipif(not PILOT.is_file(), reason='pilot.py 不存在')
def test_spec_datas_all_exist():
    """spec 里 datas 引用的文件必须都存在，缺一个安装包就少一样东西。

    同样属于「源码测试全绿、打包才炸」的类别，故在打包前用静态检查兜住。
    """
    spec = ROOT / 'Pilot.spec'
    if not spec.is_file():
        pytest.skip('Pilot.spec 不存在')
    import re
    text = spec.read_text(encoding='utf-8')
    #形如 ('assets.db', '.') 的条目
    for m in re.findall(r"\('([^']+)',\s*'\.'\)", text):
        assert (ROOT / m.replace('/', os.sep)).is_file(), f'spec 引用了不存在的文件: {m}'
    # 形如 icon=['res/icon256.ico']
    for m in re.findall(r"icon=\['([^']+)'\]", text):
        assert (ROOT / m.replace('/', os.sep)).is_file(), f'icon 引用了不存在的文件: {m}'


@pytest.mark.skipif(not (ROOT / 'setup.iss').is_file(), reason='setup.iss 不存在')
def test_inno_referenced_files_exist():
    """setup.iss 引用的源文件与图像文件必须存在，否则编译直接失败。"""
    import re
    text = (ROOT / 'setup.iss').read_text(encoding='utf-8')
    for m in re.findall(r'Source: "([^"]+)"', text):
        if '*' in m:
            assert (ROOT / m.split('\\')[0]).is_dir(), f'引用的目录不存在: {m}'
        else:
            assert (ROOT / m).is_file(), f'引用的文件不存在: {m}'
    for key in ('SetupIconFile', 'WizardImageFile', 'WizardSmallImageFile'):
        mm = re.search(rf'^{key}=(.+)$', text, re.M)
        if mm:
            assert (ROOT / mm.group(1).strip()).is_file(), \
                f'{key} 指向的文件不存在: {mm.group(1).strip()}'


@pytest.mark.skipif(not (ROOT / 'setup.iss').is_file(), reason='setup.iss 不存在')
def test_inno_exe_name_matches_spec():
    """AppExeName 必须与 spec 的 ``name=`` 一致，否则快捷方式全部失效。

    🔴 曾真实发生过：iss 写 Pilot.exe 而 spec 产 桌面伙伴-Pilot.exe，
    安装后开始菜单/桌面/开机启动的快捷方式全部指向不存在的文件。
    光看单个文件发现不了，必须**比对两处**。
    """
    import re
    spec = ROOT / 'Pilot.spec'
    if not spec.is_file():
        pytest.skip('Pilot.spec 不存在')
    iss = (ROOT / 'setup.iss').read_text(encoding='utf-8')
    m_name = re.search(r"^#define AppExeName \"(.+)\"", iss, re.M)
    m_spec = re.search(r"^\s*name='([^']+)'", spec.read_text(encoding='utf-8'), re.M)
    if not (m_name and m_spec):
        pytest.skip('无法从文件里解析出名称')
    exe = m_name.group(1)
    assert exe == f'{m_spec.group(1)}.exe', (
        f'spec 产出 {m_spec.group(1)}.exe，但 setup.iss 写的是 {exe}——'
        f'安装后快捷方式会失效')