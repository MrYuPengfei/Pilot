"""把 data/CCO/oga/audio 里的 mp3 汇集到素材包的 music/ 目录。

用法：
    python tools/collect_oga_audio.py                       # 复制到默认素材包
    python tools/collect_oga_audio.py --dst data/CCO-and-CC-BY/music
    python tools/collect_oga_audio.py --move# 移动而非复制（会清空源目录）

背景
----
素材包里各资源按「一个角色一个目录」组织（``music/<角色>/*.mp3``），
而 OGA 抓取产物是「一个 OGA 提交一个目录、里面混着 mp3/ogg/zip」。
桌宠的语音按**文件名约定**分类（早上好/中午好/晚上好/晚安 -> greeting，
``闲聊*`` -> chat，``想要了解*`` -> know），因此这里把每个 OGA 提交
目录**映射成一个独立角色目录**，不改动文件名——改名的后果是所有音频
都归到「无分类」，既无法触发问候，也丢掉了素材之间的区分。

命名上做两件事：
* 去掉 Windows 文件名非法字符；
* 目录名与 mp3 名都可能带空格/括号等，统一走 :func:`safe_dir` 清洗。

去重
----
OGA 页面上同一文件常出现两次（预览版与原版），抓取时会产生 ``xxx_0.mp3``
这种副本。按内容 MD5 去重，避免桌宠播两次同样的声音。
"""

import argparse
import hashlib
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(ROOT, 'data', 'CCO', 'oga', 'audio')
DEFAULT_DST = os.path.join(ROOT, 'data', 'CCO-and-CC-BY', 'music')

# 桌宠语音的分类前缀（见 resource_store._classify_voice）
GREETING_KEYWORDS = ('早上好', '中午好', '晚上好', '晚安')


def safe_dir(name, n=60):
    """清洗成安全的目录名；过长时截断并补上哈希避免撞名。"""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    s = re.sub(r'\s+', ' ', s)
    if len(s) > n:
        # 截断可能撞名（长目录名往往只有后缀不同），补 6 位哈希
        s = f'{s[:n - 7]}_{hashlib.md5(name.encode()).hexdigest()[:6]}'
    return s or 'unnamed'


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def classify(name):
    """按桌宠语音的命名约定给出分类，无匹配返回 None。"""
    stem = os.path.splitext(name)[0]
    if any(k in stem for k in GREETING_KEYWORDS):
        return 'greeting'
    if stem.startswith('闲聊'):
        return 'chat'
    if stem.startswith('想要了解'):
        return 'know'
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description='把 OGA 的 mp3 汇集到素材包 music/')
    ap.add_argument('--src', default=DEFAULT_SRC, help='OGA 音频源目录')
    ap.add_argument('--dst', default=DEFAULT_DST, help='素材包 music/ 目录')
    ap.add_argument('--move', action='store_true',
                    help='移动而非复制（移动后清空源目录）')
    ap.add_argument('--keep-dup', action='store_true',
                    help='不做内容去重，保留 _0 之类的副本')
    ap.add_argument('--dry-run', action='store_true', help='只报告不落盘')
    args = ap.parse_args(argv)

    if not os.path.isdir(args.src):
        sys.exit(f'源目录不存在: {args.src}')
    os.makedirs(args.dst, exist_ok=True)

    dirs = sorted(d for d in os.listdir(args.src)
                  if os.path.isdir(os.path.join(args.src, d)))
    total_files = total_bytes = 0
    skipped_dup = 0
    role_dirs = []

    for d in dirs:
        src_dir = os.path.join(args.src, d)
        mp3s = sorted(f for f in os.listdir(src_dir)
                      if f.lower().endswith('.mp3'))
        if not mp3s:
            continue
        role = safe_dir(d)
        dst_dir = os.path.join(args.dst, role)
        role_dirs.append((role, len(mp3s), dst_dir))

        seen = {}
        for f in mp3s:
            sp = os.path.join(src_dir, f)
            if not args.keep_dup:
                h = md5(sp)
                if h in seen:
                    skipped_dup += 1
                    print(f'  跳过重复 {role}/{f}（与 {seen[h]} 相同）')
                    continue
                seen[h] = f
            target = os.path.join(dst_dir, safe_dir(f, 80))
            if args.dry_run:
                print(f'  [试运行] {role}/{f}')
                continue
            # ⚠️ copy2/move **不会**自动建父目录，必须先建——
            # 否则目标角色目录还不存在时直接抛 FileNotFoundError。
            os.makedirs(dst_dir, exist_ok=True)
            if args.move:
                shutil.move(sp, target)
            else:
                shutil.copy2(sp, target)
            total_files += 1
            total_bytes += os.path.getsize(target)

    if args.move and not args.dry_run:
        # 移动后清掉源目录里空掉的提交目录，避免留下空壳
        for d in dirs:
            p = os.path.join(args.src, d)
            try:
                if os.path.isdir(p) and not os.listdir(p):
                    os.rmdir(p)
            except OSError:
                pass

    print(f'\n共 {len(role_dirs)} 个角色目录，{total_files} 个 mp3，'
          f'{total_bytes / 1048576:.1f} MB')
    if skipped_dup:
        print(f'去重跳过 {skipped_dup} 个重复文件')
    print(f'输出 -> {os.path.relpath(args.dst, ROOT)}')
    print('提示：这些是音效素材，多��不匹配问候/闲聊命名约定，'
          '导入后分类为「无分类」——可作点击等反馈音，但不会自动触发问候。')
    return 0


if __name__ == '__main__':
    sys.exit(main())