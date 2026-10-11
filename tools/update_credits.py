"""把生成的 OGA 表格注入 CREDITS.md 的附录 A 标记之间。

用法：python tools/update_credits.py
"""
import re
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDITS = os.path.join(ROOT, "CREDITS.md")
START = "<!-- OGA_TABLE_START -->"
END = "<!-- OGA_TABLE_END -->"


def main():
    tmp = os.path.join(os.environ.get("TEMP", "."), "oga_table.md")
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "tools", "gen_credits_oga.py"),
                        os.path.join(ROOT, "data", "CCO"), tmp],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        sys.exit(r.returncode)

    table = open(tmp, encoding="utf-8").read().strip()
    md = open(CREDITS, encoding="utf-8").read()

    if START not in md or END not in md:
        sys.exit("CREDITS.md 里找不到附录 A 的标记")

    new = re.sub(re.escape(START) + r".*?" + re.escape(END),
                 f"{START}\n{table}\n{END}", md, flags=re.S)
    if new == md:
        print("内容无变化")
        return
    open(CREDITS, "w", encoding="utf-8").write(new)
    print(f"已更新 {CREDITS}")


if __name__ == "__main__":
    main()