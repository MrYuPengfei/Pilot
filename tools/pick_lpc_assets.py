"""从 LPC 生成器仓库挑选桌宠实用素材，复制进 data/CC-BY/lpc/。

为什么不整个 spritesheets 搬过来：LPC 有上万张图、几百MB，
桌宠实际只需要 身体 / 头 / 眼 / 发 / 衣 几层。挑选时同步按 CREDITS.csv
筛出这些文件的授权行，生成子集 CREDITS.csv（LPC 要求随包分发署名）。
"""
import csv
import os
import shutil
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/lpc_repo"
DST = sys.argv[2] if len(sys.argv) > 2 else "data/CC-BY/lpc"

MAX_PER_DIR = 24  # 每个目录的取用上限

# 只取这些目录（桌宠够用即可，避免 88000+ 张全搬）。
# ⚠️ 路径必须与仓库实际结构一致：body 下没有 outfits，服装在 dress；
#子目录是body/bodies/<gender>。
WANT_DIRS = [
    "body/bodies/child", "body/bodies/teen", "body/bodies/female",
    "body/bodies/male", "body/bodies/skeleton", "body/bodies/zombie",
    "head", "eyes", "hair", "dress", "hat", "facial", "torso",
]


def pick_files():
    """挑选「能被 CREDITS.csv 覆盖」的 png。

    ⚠️ 关键：上游 CREDITS.csv 并**不覆盖 spritesheets 的每个文件**——
    它只有 13915 行，而实际有 88000+ 张；`body/bodies/*/walk/` 这类动作子目录
    基本没有对应行。取用**必须以 CREDITS 为准**，否则打包发行时无法履行
    CC-BY-SA 的署名义务（等于侵权）。
    """
    have = set()
    cpath = os.path.join(SRC, "CREDITS.csv")
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                have.add((row.get("filename") or "").strip())
    else:
        print("⚠️ 找不到 CREDITS.csv，无法保证署名")

    out = []
    for d in WANT_DIRS:
        p = os.path.join(SRC, "spritesheets", d)
        if not os.path.isdir(p):
            print(f"  (跳过不存在的目录 {d})")
            continue
        got = []
        for r, _, fs in os.walk(p):
            for f in sorted(fs):
                if not f.lower().endswith(".png"):
                    continue
                rel = os.path.relpath(os.path.join(r, f),
                                      os.path.join(SRC, "spritesheets"))
                rel = rel.replace("\\", "/")
                if have and rel not in have:
                    continue          # 无署名依据 → 不取
                got.append(rel)
        # 桌宠用得上的动作优先：walk（走动）/ slash（点击互动）
        got.sort(key=lambda x: (0 if any(
            k in x.rsplit("/", 1)[-1] for k in ("walk", "slash")) else 1, x))
        out.extend(got[:MAX_PER_DIR])
    return out


def main():
    files = pick_files()
    if not files:
        sys.exit("没挑到文件，检查 SRC 路径")

    os.makedirs(DST, exist_ok=True)
    copied = 0
    for rel in files:
        s = os.path.join(SRC, "spritesheets", rel)
        d = os.path.join(DST, "spritesheets", rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        copied += 1

    # CREDITS.csv 子集：filename 列与rel 对齐
    credits_src = os.path.join(SRC, "CREDITS.csv")
    subset = []
    if os.path.exists(credits_src):
        with open(credits_src, encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            want = set(files)
            for row in rd:
                fn = (row.get("filename") or "").strip()
                if fn in want:
                    subset.append(row)
    out_csv = os.path.join(DST, "CREDITS.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "notes", "authors",
                                          "licenses", "urls"])
        w.writeheader()
        w.writerows(subset)

    # 协议原文
    for name in ("LICENSE", "README.md"):
        p = os.path.join(SRC, name)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(DST, name))

    print(f"复制 {copied} 张 png")
    print(f"CREDITS.csv 子集 {len(subset)} 行 -> {out_csv}")
    if len(subset) != copied:
        print(f"⚠️ 有 {copied - len(subset)} 张图在 CREDITS.csv 里没有对应行"
              f"（上游允许，但建议复查）")


if __name__ == "__main__":
    main()