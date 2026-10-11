"""给缺少 SOURCE.md 的素材目录补写署名文件。

用途：抓取脚本早期版本没有写 SOURCE.md，中断/重启后会出现空档。
以 fetch_oga_cc0.py 产出的 json 为准回填（json 在正常跑完时才写出，
故中途失败的条目需靠日志或重抓补上）。
"""
import json
import os
import re
import sys
import time


def safe_name(s, n=60):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip(" .")
    return re.sub(r"\s+", " ", s)[:n] or "untitled"


def main():
    js = sys.argv[1]
    root = sys.argv[2]
    rows = json.load(open(js, encoding="utf-8"))
    made = skip = 0
    for r in rows:
        d = r.get("saved_to")
        if not d:
            continue
        d = d.replace("\\", "/")
        if not os.path.isdir(d):
            continue
        sm = os.path.join(d, "SOURCE.md")
        if os.path.exists(sm):
            skip += 1
            continue
        with open(sm, "w", encoding="utf-8") as f:
            f.write(f"# {r.get('title','')}\n\n"
                    f"- 作者：{r.get('author') or '未标注'}\n"
                    f"- 协议：{r.get('license')}\n"
                    f"- 来源：{r.get('url')}\n"
                    f"- 抓取日期：{time.strftime('%Y-%m-%d')}\n\n"
                    f"## 文件\n\n" +
                    "\n".join(f"- {os.path.basename(fu)}"
                              for fu in r.get("files") or []) + "\n")
        made += 1
    print(f"补写 {made} 个，已存在 {skip} 个")


if __name__ == "__main__":
    main()