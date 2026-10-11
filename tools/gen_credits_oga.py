"""扫描 data/CCO下的 SOURCE.md，生成 CREDITS.md 的「附录 A」表格。

为什么不直接读 fetch_oga_cc0.py 的 json：抓取可能中断，json 只在全部跑完才写出；
而每个素材目录落盘时就写了 SOURCE.md —— 以它为准，跑到一半也能生成清单。
"""
import os
import re
import sys


def parse(p):
    t = open(p, encoding="utf-8").read()
    # ⚠️ 必须带 re.M：SOURCE.md 是多行文本，没有它^ $ 只匹配整篇首尾
    def g(pat, default="—"):
        m = re.search(pat, t, re.M)
        return m.group(1).strip() if m else default
    return {
        "title": g(r"^#\s+(.+)$", ""),
        "author": g(r"^- 作者：(.+)$"),
        "license": g(r"^- 协议：(.+)$"),
        "url": g(r"^- 来源：(.+)$"),
        "date": g(r"^- 抓取日期：(.+)$"),
    }


def main():
    root = sys.argv[1]           # data/CCO
    out = sys.argv[2]            # CREDITS.md 片段
    only = sys.argv[3] if len(sys.argv) > 3 else ""

    rows = []
    for r, _, fs in os.walk(root):
        if "SOURCE.md" not in fs:
            continue
        p = os.path.join(r, "SOURCE.md")
        if only and only not in r:
            continue
        d = parse(p)
        # 素材文件数（不含 SOURCE.md）
        n = len([f for f in fs if f != "SOURCE.md"])
        sub = r[len(root):].replace("\\", "/").strip("/")
        rows.append((sub, d["title"], d["author"], d["license"],
                     d["url"], n))
    rows.sort()

    lines = ["| 本地目录 | 原标题 | 作者 | 协议 | 文件数 | 来源 |",
             "| --- | --- | --- | --- | --- | --- |"]
    for sub, title, author, lic, url, n in rows:
        t = title.replace("|", "\\|") or "—"
        a = author.replace("|", "\\|")
        lines.append(f"| `data/CCO/{sub}` | {t} | {a} | {lic} | {n} | {url} |")
    lines += ["", f"共 {len(rows)} 个素材条目，"
                  f"{sum(r[5] for r in rows)} 个文件。", "",
              "> 全部为 **CC0**：无需署名、可修改、可打包分发。",
              "> 每个素材目录内另有 `SOURCE.md` 记录同一信息。", ""]

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"{len(rows)} 条 -> {out}")


if __name__ == "__main__":
    main()