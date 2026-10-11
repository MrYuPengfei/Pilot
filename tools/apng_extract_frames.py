"""把 APNG 素材展开为静态 PNG 序列帧（供 png/ 普通帧目录使用）。

用法：
    python tools/apng_extract_frames.py
    python tools/apng_extract_frames.py --src data/apng-originals --dst data/CCO-png/png
    python tools/apng_extract_frames.py --max-frames 60          # 长动画截断
    python tools/apng_extract_frames.py --clean                   # 先清空目标角色目录

产物布局（与桌宠的 png/<角色> 约定一致）：
    <dst>/<角色>/0001.png
    <dst>/<角色>/0002.png
    ...

⚠️ 为什么不能直接用 pyAPNG 的``png.save()``导出帧
------------------------------------------------
pyAPNG 的 ``APNG.frames`` 给的是**未经合成的子矩形碎片**，
``FrameControl`` 里的 ``width/height/x_offset/y_offset`` 描述它在画布上的位置。
本项目素材 ``animated.png`` 就大量使用这种优化（例如帧 1 是
``121x278`` 放在偏移 ``93,14``）——直接 ``png.save()`` 得到的
是 121x278 的碎片，**丢掉画布上下文，画面会明显错位**。
（实测碎片边缘alpha=148，紧贴角色身体；正确合成帧边缘全透明。）

所以分工是：
* **pyAPNG** 负责规范的 chunk 解析（IHDR/acTL/fcTL/fdAT/PLTE…），
  它把这套繁琐的解析维护得比自己写更可靠；
* :mod:`apng_codec` 负责**帧合成**——按 dispose_op/blend_op 把碎片
  叠回全画布，产出可直接给 ``QPixmap.loadFromData`` 的整幅 PNG。

两者都缺失时回退到纯 ``apng_codec``（它不依赖 Pillow/pyAPNG）。
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools import apng_codec

# 角色名取自文件名前缀（'@' 之前）。
#   'Spinner@1x-0.8s-252px-252px.png'  -> 'Spinner'
#   'Dual Ball@1x-1.0s-256px-256px.png'-> 'Dual Ball'
#   'animated.png'                     -> 'animated'
#
# ⚠️ **只取'@' 之前会丢素材**：本目录里6 个文件的前缀都是 Spinner，
# 但规格不同（252px / 256px / 2.4s 慢速 / 3 个重名副本），
# 写进同一个 <角色>/ 会互相覆盖（实测只剩最后一份的 3 帧）。
# 故把 '@' 之后的规格一起纳入目录名，保证一个源文件对应一个独立角色目录。
SPEC_RE = re.compile(r'@(?P<spec>[^@]*)')


def role_of(filename):
    stem = os.path.splitext(filename)[0]
    role = stem.split('@', 1)[0].strip() or stem
    m = SPEC_RE.search(stem)
    if m:
        spec = re.sub(r'[\s]+', '', m.group('spec'))
        role = f'{role}_{spec}'
    v = variant_of(filename)
    if v is not None:
        role = f'{role}_{v}'
    return role


def variant_of(filename):
    """同名前缀的多个文件用括号序号区分（资源管理器重名副本）。"""
    m = re.search(r'\((\d+)\)\s*$', os.path.splitext(filename)[0])
    return int(m.group(1)) if m else None


def safe_dir(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    return re.sub(r'\s+', ' ', name) or 'unnamed'


def try_pyapng(data):
    """若装了 pyAPNG，用它取帧几何（fcTL），失败返回 None。

    用途仅限于**交叉校验**自研解析的结果；合成仍由 apng_codec 完成。
    """
    try:
        from apng import APNG
    except ImportError:
        return None
    try:
        im = APNG.from_bytes(data)
    except Exception:
        return None
    #⚠️ pyAPNG 的 FrameControl 用 ``delay``（已折算好的毫秒）而非规范里的
    # delay_num/delay_den；处置方式的属性名是 ``depose_op``（库里的拼写）。
    return [(c.width, c.height, c.x_offset, c.y_offset, int(c.delay))
            for _, c in im.frames]


def extract_one(path, out_dir, max_frames=None):
    """解一个 APNG 到 ``out_dir``，返回信息 dict。"""
    data = open(path, 'rb').read()
    if not apng_codec.is_apng(data):
        return {'file': os.path.basename(path), 'ok': False,
                'error': '不是 APNG（缺少 acTL/fcTL）'}

    width, height, declared, plays, durations = apng_codec.probe(data)
    frames = apng_codec.decode(data, max_frames=max_frames)

    info = {
        'file': os.path.basename(path),
        'ok': True,
        'canvas': f'{width}x{height}',
        'declared_frames': declared,
        'extracted_frames': len(frames),
        'truncated': bool(max_frames and declared > max_frames),
        'loop_plays': plays,
        'duration_s': round(sum(durations) / 1000, 3),
        'avg_interval_ms': round(sum(durations) / len(durations), 1) if durations else 0,
        # 展开成静态序列帧后，**只有各帧时长完全一致**才能忠实还原节奏；
        # 否则只能退化成「按平均间隔匀速播」，这里明确标记以便选用。
        # （实测Cube 各帧是 33/34ms 混合，属非均匀；animated 全 40ms 属均匀）
        'uniform_timing': len(set(durations)) <= 1,
        'distinct_durations_ms': sorted(set(durations)),
    }

    # 交叉校验：pyAPNG 解析出的帧数应与自研一致
    ref = try_pyapng(data)
    if ref is not None:
        info['pyapng_frames'] = len(ref)
        if len(ref) != declared:
            info['warning'] = (f'pyAPNG 解析出 {len(ref)} 帧，'
                               f'acTL 声明 {declared} 帧')

    os.makedirs(out_dir, exist_ok=True)
    for fr in frames:
        # 4 位补零，保证文件名字典序 == 播放顺序
        with open(os.path.join(out_dir, f'{fr.index + 1:04d}.png'), 'wb') as f:
            f.write(fr.png)
    return info


def rel_display(path):
    """相对项目根显示；跨盘符时 relpath 会抛 ValueError，退回绝对路径。"""
    try:
        return os.path.relpath(path, ROOT).replace('\\', '/')
    except ValueError:
        return path.replace('\\', '/')


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='把 APNG 展开为静态 PNG 序列帧（使用 pyAPNG 解析 + apng_codec 合成）')
    ap.add_argument('--src', default=os.path.join(ROOT, 'data', 'apng-originals'),
                    help='APNG 源目录')
    ap.add_argument('--dst', default=os.path.join(ROOT, 'data', 'CCO-and-CC-BY', 'png'),
                    help='输出目录（角色子目录直接落在这里）')
    ap.add_argument('--max-frames', type=int, default=None,
                    help='每个文件最多提取多少帧（超长动画截断，避免几百个文件）')
    ap.add_argument('--clean', action='store_true',
                    help='提取前清空目标目录')
    args = ap.parse_args(argv)

    if not os.path.isdir(args.src):
        sys.exit(f'源目录不存在: {args.src}')
    # 用 find_spec 探测而非 import：装了才提示，不装也照常跑（仅少交叉校验）
    if importlib.util.find_spec('apng') is not None:
        print('使用 pyAPNG 解析 + apng_codec 合成')
    else:
        print('未安装 pyAPNG，仅用 apng_codec（功能等价，仅少一层交叉校验）')

    if args.clean and os.path.isdir(args.dst):
        shutil.rmtree(args.dst)
    os.makedirs(args.dst, exist_ok=True)

    files = sorted(f for f in os.listdir(args.src) if f.lower().endswith('.png'))
    if not files:
        sys.exit(f'{args.src} 里没有 PNG 文件')

    reports, total_frames, total_bytes = [], 0, 0
    for name in files:
        role = role_of(name)
        out_dir = os.path.join(args.dst, safe_dir(role))
        info = extract_one(os.path.join(args.src, name), out_dir, args.max_frames)
        info['role'] = os.path.basename(out_dir)
        info['role_dir'] = rel_display(out_dir)
        reports.append(info)

        if info['ok']:
            total_frames += info['extracted_frames']
            size = sum(os.path.getsize(os.path.join(out_dir, f))
                       for f in os.listdir(out_dir))
            total_bytes += size
            print(f"  {name[:38]:40s} -> {info['role']}/  "
                  f"{info['extracted_frames']}帧 "
                  f"{info['canvas']} {info['duration_s']}s "
                  f"{size / 1024:.0f}KB")
        else:
            print(f"  {name[:38]:40s} 跳过：{info['error']}")

    manifest = os.path.join(args.dst, 'frames_manifest.json')
    with open(manifest, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=1)

    print(f'\n共 {len(reports)} 个文件，提取 {total_frames} 帧，'
          f'{total_bytes / 1048576:.1f} MB')
    print(f'清单 -> {rel_display(manifest)}')
    # ⚠️ **有跳过项不算失败**：素材目录里混入非 APNG（普通静态 PNG、预览图）
    # 是常态，脚本应把它们记进清单后继续。只有「一个都没解出来」才该报错。
    bad = [r for r in reports if not r['ok']]
    if bad:
        print(f'跳过 {len(bad)} 个非 APNG 文件（已记入清单）')
    if not total_frames:
        sys.exit('没有提取到任何帧：源目录里可能都不是 APNG')
    return 0


if __name__ == '__main__':
    sys.exit(main())