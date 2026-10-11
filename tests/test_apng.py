"""APNG 支持的测试：解码器、存储层、导入导出往返。

**不依赖仓库里的真实素材**：用 :func:`make_apng` 现场合成最小 APNG，
这样素材被替换/删除时测试仍然有效；真实素材另有一项冒烟测试。
"""

import struct
import sys
import zlib
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / 'tools'))

from tools import apng_codec
import apng_extract_frames  # noqa: E402  解帧脚本（测试其命名与产物）
from tools.apng_codec import ApngError  # noqa: E402
from asset_exporter import export_assets  # noqa: E402
from asset_importer import import_assets  # noqa: E402
from resource_store import ResourceStore  # noqa: E402


# ---------- 合成最小 APNG ----------

def _chunk(ctype, body):
    return (struct.pack('>I', len(body)) + ctype + body
            + struct.pack('>I', zlib.crc32(ctype + body) & 0xFFFFFFFF))


def make_apng(width=4, height=4, frames=3, delay_ms=40, plays=0,
              fctl_before_idat=True, dispose=0, blend=0):
    """合成一个最小 APNG。

    :param fctl_before_idat: True = 第 0 帧用 IDAT（``acTL, fcTL, IDAT, fcTL, fdAT…``，
        真实素材的布局）；False = 静态预览图在前（``acTL, IDAT, fcTL, fdAT…``）。
    :param dispose: 0=NONE 1=BACKGROUND 2=PREVIOUS
    :param blend: 0=SOURCE 1=OVER
    """
    sig = apng_codec.PNG_SIGNATURE
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    actl = struct.pack('>II', frames, plays)
    out = [_chunk(b'IHDR', ihdr), _chunk(b'acTL', actl)]

    def raw_pixels(rgba):
        """整帧扫描线数据：每行前缀 filter type 0，共 height 行。

        ⚠️ 必须逐行拼接——只写一行会让解码器读到越界的垃圾字节，
        报出「未知的 PNG 滤波器类型」。
        """
        row = bytes([0]) + bytes(rgba) * width
        return row * height

    def frame_ctl(seq):
        return _chunk(b'fcTL', struct.pack(
            '>IIIIIHHBB', seq, width, height, 0, 0,
            delay_ms, 1000, dispose, blend))

    if fctl_before_idat:
        # 第 0 帧：fcTL 在 IDAT 之前，帧数据即IDAT
        out.append(frame_ctl(0))
        out.append(_chunk(b'IDAT', zlib.compress(raw_pixels([255, 0, 0, 255]))))
        seq = 1
    else:
        # 静态预览图：IDAT 先行，不属于任何帧
        out.append(_chunk(b'IDAT', zlib.compress(raw_pixels([0, 0, 255, 255]))))
        seq = 0

    for i in range(1 if fctl_before_idat else 0, frames):
        if not fctl_before_idat:
            out.append(frame_ctl(seq))
        else:
            out.append(frame_ctl(seq))
        seq += 1
        data = zlib.compress(raw_pixels([0, 255, 0, 255]))
        out.append(_chunk(b'fdAT', struct.pack('>I', seq) + data))
        seq += 1

    out.append(_chunk(b'IEND', b''))
    return sig + b''.join(out)


# ---------- 解码器 ----------

def test_is_apng():
    assert apng_codec.is_apng(make_apng())
    assert not apng_codec.is_apng(b'not a png')
    # 普通静态 PNG 不应被误判
    static = apng_codec.PNG_SIGNATURE + _chunk(
        b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 6, 0, 0, 0)) \
             + _chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00\xff')) \
             + _chunk(b'IEND', b'')
    assert not apng_codec.is_apng(static)


def test_probe_reads_metadata():
    data = make_apng(width=8, height=6, frames=4, delay_ms=50, plays=3)
    w, h, n, plays, durations = apng_codec.probe(data)
    assert (w, h) == (8, 6)
    assert n == 4
    assert plays == 3
    assert durations == [50] * 4


def test_decode_frame_count_matches_actl():
    """帧数必须与 acTL 声明一致——这是最容易出错的地方（IDAT/fdAT 归属）。"""
    for n in (1, 2, 5, 12):
        data = make_apng(frames=n)
        frames = apng_codec.decode(data)
        assert len(frames) == n, f'acTL={n} 但解出 {len(frames)} 帧'
        assert apng_codec.frame_count(data) == n


def test_decode_both_layouts():
    """两种 IDAT/fcTL 相对布局都要正确处理。

    「IDAT 在前」是静态预览图布局，若把它误当第 0 帧，
    帧数会多 1 且首帧颜色变成预览图的蓝色。
    """
    a = apng_codec.decode(make_apng(frames=3, fctl_before_idat=True))
    assert len(a) == 3
    b = apng_codec.decode(make_apng(frames=3, fctl_before_idat=False))
    assert len(b) == 3


def test_decode_respects_max_frames():
    data = make_apng(frames=20)
    assert len(apng_codec.decode(data, max_frames=5)) == 5


def test_frame_duration_and_index():
    frames = apng_codec.decode(make_apng(frames=4, delay_ms=80))
    for i, fr in enumerate(frames):
        assert fr.index == i
        assert fr.duration_ms == 80


def test_duration_den_zero_falls_back_to_100():
    """delay_den=0 时按 100 处理（规范），且结果不得为 0ms（会变成忙循环）。"""
    sig = apng_codec.PNG_SIGNATURE
    ihdr = struct.pack('>IIBBBBB', 2, 2, 8, 6, 0, 0, 0)
    actl = struct.pack('>II', 2, 0)
    fctl0 = _chunk(b'fcTL', struct.pack('>IIIIIHHBB',
                                        0, 2, 2, 0, 0, 10, 0, 0, 0))
    fctl1 = _chunk(b'fcTL', struct.pack('>IIIIIHHBB',
                                        2, 2, 2, 0, 0, 10, 0, 0, 0))
    # 2x2 RGBA = 每行 8 字节像素 + 1 字节 filter，共 2 行
    px = zlib.compress((bytes([0]) + bytes([255, 0, 0, 255] * 2)) * 2)
    data = (sig + _chunk(b'IHDR', ihdr) + _chunk(b'acTL', actl) + fctl0
            + _chunk(b'IDAT', px) + fctl1
            + _chunk(b'fdAT', struct.pack('>I', 3) + px)
            + _chunk(b'IEND', b''))
    frames = apng_codec.decode(data)
    assert len(frames) == 2
    # 10/100 秒 = 100ms
    assert frames[0].duration_ms == 100
    assert all(f.duration_ms > 0 for f in frames)


def test_dispose_operations_produce_valid_frames():
    """三种dispose_op 都要产出可解码的帧（合成器不能崩或漏画）。"""
    for dispose in (0, 1, 2):
        data = make_apng(frames=4, dispose=dispose)
        frames = apng_codec.decode(data)
        assert len(frames) == 4
        for fr in frames:
            assert fr.png.startswith(apng_codec.PNG_SIGNATURE)


def test_blend_over_operations():
    for blend in (0, 1):
        frames = apng_codec.decode(make_apng(frames=3, blend=blend))
        assert len(frames) == 3


def test_reject_non_apng():
    with pytest.raises(ApngError):
        apng_codec.decode(b'garbage')


def test_reject_png_without_signature():
    with pytest.raises(ApngError):
        apng_codec.decode(b'\x00' * 32)


# ---------- 真实素材冒烟 ----------

REAL_APNG_DIR = ROOT_DIR / 'data' / 'apng'


@pytest.mark.skipif(not REAL_APNG_DIR.is_dir(), reason='未提供真实 APNG 素材')
def test_real_assets_decode():
    """仓库里的真实素材必须能解出，且时长与文件名标注一致。"""
    files = sorted(REAL_APNG_DIR.glob('*.png'))
    if not files:
        pytest.skip('没有真实素材')
    for f in files:
        data = f.read_bytes()
        assert apng_codec.is_apng(data), f'{f.name} 不是 APNG'
        w, h, n, plays, durations = apng_codec.probe(data)
        assert w > 0 and h > 0 and n > 0
        assert all(d > 0 for d in durations)
        frames = apng_codec.decode(data, max_frames=3)
        assert len(frames) == min(3, n)
        for fr in frames:
            assert fr.png.startswith(apng_codec.PNG_SIGNATURE)


# ---------- 解帧脚本 ----------

def test_role_of_strips_spec():
    """角色名要把 '@' 之后的规格纳入，否则同前缀的不同规格会互相覆盖。"""
    assert apng_extract_frames.role_of('Cube@1x-1.0s-200px-200px.png') == 'Cube_1x-1.0s-200px-200px'
    assert apng_extract_frames.role_of('Dual Ball@1x-1.0s-256px-256px.png') \
        == 'Dual Ball_1x-1.0s-256px-256px'
    assert apng_extract_frames.role_of('animated.png') == 'animated'


def test_role_of_unique_per_file(tmp_path):
    """同一目录里的每个源文件都必须映射到**唯一**角色名。"""
    names = [
        'Spinner@1x-0.8s-252px-252px.png',
        'Spinner@1x-0.8s-256px-256px.png',
        'Spinner@1x-0.8s-256px-256px (1).png',
        'Spinner@1x-0.8s-256px-256px (2).png',
        'Spinner@1x-0.8s-256px-256px (3).png',
        'Spinner@1x-2.4s-256px-256px.png',
    ]
    roles = [apng_extract_frames.role_of(n) for n in names]
    assert len(set(roles)) == len(names), f'角色名冲突: {roles}'


def test_safe_dir_strips_illegal_chars():
    assert apng_extract_frames.safe_dir('a/b\\c:d') == 'a_b_c_d'
    assert apng_extract_frames.safe_dir('...') == 'unnamed'


def test_extract_writes_numbered_frames(tmp_path):
    """解出的帧必须是 0001.png 起的连续序号——排序即播放顺序。"""
    src = tmp_path / 'src'
    src.mkdir()
    (src / 'Cube@1x-1.0s-200px-200px.png').write_bytes(make_apng(frames=4))
    dst = tmp_path / 'out'
    rc = apng_extract_frames.main(
        ['--src', str(src), '--dst', str(dst)])
    assert rc == 0
    role_dir = dst / 'Cube_1x-1.0s-200px-200px'
    got = sorted(p.name for p in role_dir.glob('*.png'))
    assert got == ['0001.png', '0002.png', '0003.png', '0004.png']
    assert (dst / 'frames_manifest.json').is_file()


def test_extract_respects_max_frames(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    (src / 'Cube@1x-1.0s-200px-200px.png').write_bytes(make_apng(frames=10))
    dst = tmp_path / 'out'
    apng_extract_frames.main(['--src', str(src), '--dst', str(dst),
                              '--max-frames', '4'])
    role_dir = dst / 'Cube_1x-1.0s-200px-200px'
    assert len(list(role_dir.glob('*.png'))) == 4


def test_extract_skips_non_apng(tmp_path):
    """非 APNG 文件要被跳过并记进清单，而不是整个脚本报错退出。"""
    src = tmp_path / 'src'
    src.mkdir()
    (src / 'Cube@1x-1.0s-200px-200px.png').write_bytes(make_apng(frames=2))
    (src / 'static.png').write_bytes(b'\x89PNG\r\n\x1a\nnot really')
    dst = tmp_path / 'out'
    apng_extract_frames.main(['--src', str(src), '--dst', str(dst)])
    import json
    man = json.loads((dst / 'frames_manifest.json').read_text(encoding='utf-8'))
    bad = [m for m in man if not m['ok']]
    assert len(bad) == 1
    assert not (dst / 'static').exists()


def test_extract_output_matches_codec(tmp_path):
    """脚本落盘的帧内容必须与 apng_codec 直接解出的完全一致。"""
    src = tmp_path / 'src'
    src.mkdir()
    data = make_apng(frames=3, delay_ms=40)
    (src / 'Cube@1x-1.0s-200px-200px.png').write_bytes(data)
    dst = tmp_path / 'out'
    apng_extract_frames.main(['--src', str(src), '--dst', str(dst)])
    role_dir = dst / 'Cube_1x-1.0s-200px-200px'
    expected = apng_codec.decode(data)
    for i, fr in enumerate(expected, 1):
        assert (role_dir / f'{i:04d}.png').read_bytes() == fr.png


REAL_EXTRACT_DIR = ROOT_DIR / 'data' / 'CCO-and-CC-BY' / 'png'


@pytest.mark.skipif(not REAL_EXTRACT_DIR.is_dir(), reason='未生成解帧产物')
def test_extracted_assets_have_contiguous_frames():
    """真实产物：每个角色目录的帧号必须从 0001 连续递增。"""
    roles = [d for d in REAL_EXTRACT_DIR.iterdir() if d.is_dir()]
    if not roles:
        pytest.skip('没有解帧产物')
    for r in roles:
        nums = sorted(int(p.stem) for p in r.glob('*.png'))
        assert nums, f'{r.name} 没有帧'
        assert nums[0] == 1, f'{r.name} 起始帧号不是 1'
        assert nums == list(range(1, len(nums) + 1)), f'{r.name} 帧号不连续'


# ---------- 存储层 ----------

@pytest.fixture()
def tree_with_apng(tmp_path):
    """含 png 角色、apng 角色、以及两者都有的角色。"""
    (tmp_path / 'png' / '帧角色').mkdir(parents=True)
    (tmp_path / 'png' / '帧角色' / '1.png').write_bytes(b'PNG-FRAME')
    (tmp_path / 'apng' / '动画角色').mkdir(parents=True)
    (tmp_path / 'apng' / '动画角色' / 'spin.png').write_bytes(make_apng(frames=2))
    (tmp_path / 'apng' / '帧角色').mkdir(parents=True)
    (tmp_path / 'apng' / '帧角色' / 'idle.png').write_bytes(make_apng(frames=2))
    return tmp_path


def test_store_lists_apng_filesystem(tree_with_apng):
    store = ResourceStore(str(tree_with_apng))
    assert store.backend == 'filesystem'
    assert store.list_apng('动画角色') == ['spin.png']
    assert store.list_apng('不存在') == []
    assert store.read_apng('动画角色', 'spin.png')


def test_apng_only_role_is_a_role(tree_with_apng):
    """只有 apng、没有 png 帧的角色也必须出现在人物列表里。"""
    store = ResourceStore(str(tree_with_apng))
    roles = store.list_roles()
    assert '动画角色' in roles
    assert '帧角色' in roles


def test_stats_include_apng(tree_with_apng):
    store = ResourceStore(str(tree_with_apng))
    st = store.stats()
    assert st['apngs'] == 2
    assert st['frames'] == 1


# ---------- 导入导出往返 ----------

def test_import_apng(tmp_path):
    src = tmp_path / 'pack'
    (src / 'apng' / '阿狸').mkdir(parents=True)
    (src / 'apng' / '阿狸' / 'a.png').write_bytes(make_apng(frames=2))
    db = tmp_path / 'assets.db'
    report = import_assets(str(src), str(db))
    assert report['apngs'] == 1
    assert report['new_roles'] == ['阿狸']
    assert '阿狸' in report['roles']

    store = ResourceStore(str(tmp_path))
    assert store.list_apng('阿狸') == ['a.png']
    assert store.read_apng('阿狸', 'a.png')


def test_import_apng_registers_role(tmp_path):
    """只导入 APNG 的角色也要登记进 config（否则人物菜单里选不到）。"""
    import config_store as cs

    src = tmp_path / 'pack'
    (src / 'apng' / '仅动画').mkdir(parents=True)
    (src / 'apng' / '仅动画' / 'a.png').write_bytes(make_apng(frames=2))
    db = tmp_path / 'assets.db'
    cfg = tmp_path / 'config.db'
    conf = cs.ConfigStore(str(cfg))
    import_assets(str(src), str(db), conf)
    assert '仅动画' in conf.roles()


def test_export_apng_dir(tmp_path):
    src = tmp_path / 'pack'
    (src / 'apng' / '阿狸').mkdir(parents=True)
    (src / 'apng' / '阿狸' / 'a.png').write_bytes(make_apng(frames=2))
    db = tmp_path / 'assets.db'
    import_assets(str(src), str(db))

    store = ResourceStore(str(tmp_path))
    out = tmp_path / 'out'
    rep = export_assets(store, str(out))
    assert rep['files'] == 1
    assert (out / 'apng' / '阿狸' / 'a.png').is_file()


def test_export_apng_zip(tmp_path):
    src = tmp_path / 'pack'
    (src / 'apng' / '阿狸').mkdir(parents=True)
    (src / 'apng' / '阿狸' / 'a.png').write_bytes(make_apng(frames=2))
    db = tmp_path / 'assets.db'
    import_assets(str(src), str(db))

    store = ResourceStore(str(tmp_path))
    zpath = tmp_path / 'out.zip'
    export_assets(store, str(zpath), as_zip=True)
    import zipfile
    with zipfile.ZipFile(zpath) as zf:
        assert 'apng/阿狸/a.png' in zf.namelist()


def test_roundtrip_preserves_bytes(tmp_path):
    """导出→再导入，APNG 字节必须**完全一致**（可逆）。"""
    original = make_apng(width=6, height=5, frames=4, delay_ms=33)
    src = tmp_path / 'pack'
    (src / 'apng' / '角色A').mkdir(parents=True)
    (src / 'apng' / '角色A' / 'anim.png').write_bytes(original)
    db = tmp_path / 'assets.db'
    import_assets(str(src), str(db))

    store = ResourceStore(str(tmp_path))
    out = tmp_path / 'out'
    export_assets(store, str(out))

    # 导入导出后的目录，字节应一致
    exported = (out / 'apng' / '角色A' / 'anim.png').read_bytes()
    assert exported == original

    # 再导回另一个库，解码结果也应一致
    db2 = tmp_path / 'assets2.db'
    import_assets(str(out), str(db2))
    store2 = ResourceStore(str(tmp_path), db_name='assets2.db')
    again = store2.read_apng('角色A', 'anim.png')
    assert again == original
    assert apng_codec.decode(again)[0].png == \
           apng_codec.decode(original)[0].png


def test_roundtrip_with_frames_and_apng(tmp_path):
    """png 帧与 APNG 混合的角色，往返后两者都在。"""
    (tmp_path / 'pack' / 'png' / '混合').mkdir(parents=True)
    (tmp_path / 'pack' / 'png' / '混合' / '1.png').write_bytes(b'PNG')
    (tmp_path / 'pack' / 'apng' / '混合').mkdir(parents=True)
    (tmp_path / 'pack' / 'apng' / '混合' / 'a.png').write_bytes(make_apng(frames=2))

    db = tmp_path / 'assets.db'
    rep = import_assets(str(tmp_path / 'pack'), str(db))
    assert rep['frames'] == 1 and rep['apngs'] == 1

    store = ResourceStore(str(tmp_path))
    out = tmp_path / 'out'
    export_assets(store, str(out))
    assert (out / 'png' / '混合' / '1.png').is_file()
    assert (out / 'apng' / '混合' / 'a.png').is_file()


def test_export_filters_roles(tmp_path):
    """``roles=[]`` 表示一个都不要，APNG 也要被过滤掉。"""
    for role in ('甲', '乙'):
        (tmp_path / 'pack' / 'apng' / role).mkdir(parents=True)
        (tmp_path / 'pack' / 'apng' / role / 'a.png').write_bytes(
            make_apng(frames=2))
    db = tmp_path / 'assets.db'
    import_assets(str(tmp_path / 'pack'), str(db))
    store = ResourceStore(str(tmp_path))

    out = tmp_path / 'onlyA'
    export_assets(store, str(out), roles=['甲'])
    assert (out / 'apng' / '甲' / 'a.png').is_file()
    assert not (out / 'apng' / '乙').exists()

    with pytest.raises(ValueError):
        export_assets(store, str(tmp_path / 'none'), roles=[])


def test_delete_role_removes_apng(tmp_path):
    (tmp_path / 'pack' / 'apng' / '待删').mkdir(parents=True)
    (tmp_path / 'pack' / 'apng' / '待删' / 'a.png').write_bytes(make_apng(frames=2))
    db = tmp_path / 'assets.db'
    import_assets(str(tmp_path / 'pack'), str(db))
    store = ResourceStore(str(tmp_path))
    store.delete_role('待删')
    # 关连接重开新实例，验证真的落盘删除
    store.close()
    store2 = ResourceStore(str(tmp_path))
    assert store2.list_apng('待删') == []
    assert '待删' not in store2.list_roles()


# ---------- 素材包目录结构（data/CCO-and-CC-BY） ----------

PACK_DIR = ROOT_DIR / 'data' / 'CCO-and-CC-BY'


@pytest.mark.skipif(not PACK_DIR.is_dir(), reason='素材包目录不存在')
def test_pack_is_importable_as_asset_pack():
    """整个素材包要能被 build_assets_db 识别——即目录层级完全符合导入约定。

    约定： ``png/<角色>/*.png`` -> frame，``music/<角色>/*.mp3`` -> voice。
    一旦层级错位（如多套一层、放到 apng/ 下），桌宠就选不到这些素材。
    """
    sys.path.insert(0, str(ROOT_DIR / 'tools'))
    from build_assets_db import iter_assets

    rows = list(iter_assets(str(PACK_DIR)))
    kinds = {k for _, k, _, _, _ in rows}
    assert rows, '素材包里没有任何可识别资源'
    assert 'frame' in kinds, 'png/ 下没有可识别的帧'
    assert (PACK_DIR / 'png').is_dir()
    assert (PACK_DIR / 'music').is_dir()


@pytest.mark.skipif(not (PACK_DIR / 'music').is_dir(), reason='music 目录不存在')
def test_pack_music_dirs_are_bgm():
    """每个 music 子目录都必须含 background.mp3。

    🔴 桌宠靠**文件名**判定地区 BGM：``music/<地区>/background.mp3`` 才被
    ``iter_assets`` 识别成 ``kind='bgm'``；叫别的名字就变成角色语音，
    播放入口完全不同（不进托盘 BGM 菜单）。
    """
    missing = [d.name for d in (PACK_DIR / 'music').iterdir()
               if d.is_dir() and not (d / 'background.mp3').is_file()]
    assert not missing, f'这些地区缺 background.mp3: {missing}'


@pytest.mark.skipif(not (PACK_DIR / 'music').is_dir(), reason='music 目录不存在')
def test_pack_bgm_recognized_as_bgm_kind():
    """地区 BGM 必须被识别成 kind='bgm'，而不是角色语音。"""
    sys.path.insert(0, str(ROOT_DIR / 'tools'))
    from build_assets_db import iter_assets

    rows = [r for r in iter_assets(str(PACK_DIR)) if r[1] == 'bgm']
    assert rows, '没有任何条目被识别为 BGM（检查文件名是否叫 background.mp3）'
    for role, _kind, name, _cat, _path in rows:
        assert name == 'background.mp3'


@pytest.mark.skipif(not (PACK_DIR / 'png').is_dir(), reason='png 目录不存在')
def test_pack_frame_numbering_contiguous():
    """帧目录里的序号必须 0001 起连续——排序即播放顺序，断号会导致跳帧。"""
    for role in (PACK_DIR / 'png').iterdir():
        if not role.is_dir():
            continue
        nums = sorted(int(p.stem) for p in role.glob('*.png'))
        assert nums, f'{role.name} 没有帧'
        assert nums[0] == 1, f'{role.name} 起始帧号不是 1'
        assert nums == list(range(1, len(nums) + 1)), f'{role.name} 帧号不连续'