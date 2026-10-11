"""抓取 OpenGameArt 上带 CC0 标签的资源文件。

只接受页面 license 区明确出现 CC0 的条目（CC-BY 等归到cc-by 目录另行处理）。
输出 JSON 清单：[{slug,title,url,author,license,files:[...]}]
"""
import json
import os
import re
import sys
import time
import urllib.parse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
BASE = "https://opengameart.org"
HEADERS = {
    "User-Agent": UA,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def session():
    return requests.Session()


def get(s, url, tries=4):
    """OGA 对非浏览器指纹会回 404，且代理偶发 502 —— 两者都重试。"""
    last = None
    for i in range(tries):
        try:
            r = s.get(url, timeout=40, headers=HEADERS)
        except requests.RequestException as e:  # 代理 502 / 连接重置
            last = e
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 200:
            return r
        last = RuntimeError(f"HTTP {r.status_code}")
        # 404 有时是反爬伪装，重试无望但仍给一次机会
        time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"GET {url} 失败: {last}")


CC0_TID = 4  # field_art_licenses_tid 里 CC0 的取值

# 音频+图形都收
EXT = (".ogg", ".mp3", ".wav", ".flac", ".m4a", ".zip", ".png", ".gif")

TYPE_TID = {12: "music", 13: "soundeffect", 9: "2dart", 10: "3dart"}


def browse(s, tid, pages=3):
    """列出「该类型 + CC0」的条目。

    两个反爬/易错点：
    1) /content/browse 那条路返回的是侧栏「New Art Collections」（协议不限），
       必须走 art-search-advanced + field_art_licenses_tid 才真正过滤。
    2) 结果区是 view-display-id-search_art_advanced，条目标题在
       span.art-preview-title 里；分页参数名带索引（[0]），不能写成裸key。
    """
    out = []
    for page in range(pages):
        url = (f"{BASE}/art-search-advanced?keys="
               f"&field_art_type_tid%5B0%5D={tid}"
               f"&field_art_licenses_tid%5B0%5D={CC0_TID}"
               f"&sort_by=count&sort_order=DESC")
        if page:
            url += f"&page={page}"
        h = get(s, url).text
        seg = h[h.find("view-display-id-search_art_advanced"):]
        if not seg:
            break
        rows = re.findall(r'<span class="art-preview-title">'
                          r'<a href="(/content/[^"#?]+)"', seg)
        if not rows:
            break
        got = []
        names = set()
        for sl in rows:
            name = urllib.parse.unquote(sl.rsplit("/", 1)[-1])
            if name in names:
                continue
            names.add(name)
            got.append((name, f"{BASE}{sl}"))
        out.extend(got)
        time.sleep(1.0)
    return out


def detail(s, slug, url):
    """抓单页：标题、作者、协议、附件直链。"""
    r = get(s, url)
    if "text/html" not in r.headers.get("Content-Type", ""):
        return None
    h = r.text

    #标题：<title> 是 "标题 | OpenGameArt.org"（取**前**段）；
    # 页面里唯一的 <h2 class="title"> 是侧栏 "Comments"，不能用来判标题。
    title = ""
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    if m:
        raw = re.sub(r"<[^>]+>", " ", m.group(1))
        raw = re.sub(r"\s+", " ", raw).strip()
        head = re.split(r"\s*[|–]\s*", raw)[0].strip()
        if head and head.lower() != "open game art" and head.lower() != "comments":
            title = head
    title = title or slug

    author = ""
    m = re.search(r'class="username"[^>]*>([^<]+)<', h)
    if m:
        author = m.group(1).strip()

    #协议由列表页 licenses_tid=CC0 严格过滤保证（详情页该字段是懒加载的，HTML 里根本没有）
    lic = "CC0"

    # 附件：只认真实媒体/压缩包，跳过 css/js/缩略图/audio_preview 试听转码版
    files = []
    for m in re.finditer(r'href="(https://opengameart\.org/sites/default/files/[^"]+)"', h):
        u = m.group(1).replace("&amp;", "&")
        if "audio_preview" in u or "/styles/" in u:
            continue
        if not u.lower().endswith(EXT):
            continue
        if u not in files:
            files.append(u)
    # 试听条的 data-mp3-url 指向的就是原始 mp3（非转码版），一并收
    for m in re.finditer(r"data-mp3-url='([^']+\.mp3)'", h):
        u = m.group(1)
        if "audio_preview" not in u and u not in files:
            files.append(u)

    return {"slug": slug, "title": title, "url": url,
            "author": author, "license": lic, "files": files,
            "exts": sorted({os.path.splitext(f)[1].lower() for f in files})}


def safe_name(s, n=60):
    """把标题洗成安全的目录名，保留原名可读性。"""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip(" .")
    s = re.sub(r"\s+", " ", s)
    return (s[:n] or "untitled")


def download(s, url, dest, max_bytes=25 * 1024 * 1024):
    """流式下载；返回字节数，失败/超限返回 0。

    设体积上限：CC0 音乐站里有些上百 MB 的合集包，对桌宠 BGM 毫无用处。
    必须**边下边判**——用 r.content 会在知道大小前就把整个包收进内存。
    """
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return os.path.getsize(dest)

    last = None
    for attempt in range(3):
        try:
            r = s.get(url, timeout=60, headers=HEADERS, stream=True)
            if r.status_code != 200:
                last = RuntimeError(f"HTTP {r.status_code}")
                r.close()
                time.sleep(1.0 * (attempt + 1))
                continue
            clen = r.headers.get("Content-Length")
            if clen and int(clen) > max_bytes:
                print(f"  跳过(声明 {int(clen)//1048576}MB): {url}", file=sys.stderr)
                r.close()
                return 0
            tmp = dest + ".part"
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            got = 0
            over = False
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    got += len(chunk)
                    if got > max_bytes:
                        over = True
                        break
                    f.write(chunk)
            r.close()
            if over:
                os.remove(tmp)
                print(f"  跳过(超 {max_bytes//1048576}MB): {url}", file=sys.stderr)
                return 0
            os.replace(tmp, dest)
            return got
        except Exception as e:
            last = e
            time.sleep(1.0 * (attempt + 1))
    print(f"  下载失败 {url}: {last}", file=sys.stderr)
    return 0


def search(s, keys, tid=9, limit=6):
    """按关键词搜 CC0 条目（tid=9 是 2D Art）。"""
    u = (f"{BASE}/art-search-advanced?keys={urllib.parse.quote(keys)}"
         f"&field_art_type_tid%5B0%5D={tid}"
         f"&field_art_licenses_tid%5B0%5D={CC0_TID}"
         f"&sort_by=count&sort_order=DESC")
    h = get(s, u).text
    seg = h[h.find("view-display-id-search_art_advanced"):]
    rows = re.findall(r'<span class="art-preview-title">'
                      r'<a href="(/content/[^"#?]+)"', seg)
    out, seen = [], set()
    for r in rows:
        name = urllib.parse.unquote(r.rsplit("/", 1)[-1])
        if name not in seen:
            seen.add(name)
            out.append((name, f"{BASE}{r}"))
    return out[:limit]


def main():
    tids = [int(x) for x in sys.argv[1].split(",")]
    pages = int(sys.argv[2])
    outjson = sys.argv[3]
    # 可选第5参数：--download <目标根目录>  才会真正落盘
    dl_root = None
    if "--download" in sys.argv:
        dl_root = sys.argv[sys.argv.index("--download") + 1]
    # --keys "a|b|c"：改用关键词搜索（每个词最多取 limit 条）
    keys = None
    if "--keys" in sys.argv:
        keys = [k for k in sys.argv[sys.argv.index("--keys") + 1].split("|") if k]
    sub_dir = "misc"
    if "--subdir" in sys.argv:
        sub_dir = sys.argv[sys.argv.index("--subdir") + 1]

    s = session()
    seen = {}
    if keys:
        for k in keys:
            for slug, url in search(s, k, tid=tids[0], limit=6):
                seen.setdefault(slug, url)
            time.sleep(1.0)
    else:
        for tid in tids:
            for slug, url in browse(s, tid, pages):
                seen.setdefault(slug, url)
    print(f"发现 {len(seen)} 个 CC0 条目", file=sys.stderr)

    rows = []
    for i, (slug, url) in enumerate(sorted(seen.items()), 1):
        try:
            d = detail(s, slug, url)
        except Exception as e:
            print(f"[{i}/{len(seen)}] {slug} 详情失败: {e}", file=sys.stderr)
            continue
        if not (d and d["files"]):
            print(f"[{i}/{len(seen)}] {slug} 无附件，跳过", file=sys.stderr)
            continue
        rows.append(d)

        if dl_root:
            # 目录按**附件实际形态**归类，而不是 tids[0]——
            # 一次跑多个 tid（13音效 + 12音乐）时，用 tids[0] 会把音乐也塞进soundeffect。
            IMAGE = {".png", ".gif"}
            exts = set(d.get("exts") or [])
            if exts and exts <= IMAGE:
                this_sub = "sprites"
            elif exts & IMAGE:
                this_sub = "mixed"
            else:
                this_sub = "audio"
            dest_dir = os.path.join(dl_root, this_sub, safe_name(d["title"]))
            got = 0
            for fu in d["files"]:
                fn = os.path.basename(urllib.parse.unquote(fu))
                n = download(s, fu, os.path.join(dest_dir, fn))
                got += n
            d["saved_to"] = dest_dir
            d["bytes"] = got
            # 署名信息随素材走：即使日后 CREDITS.md 丢失，目录内仍有出处
            try:
                os.makedirs(dest_dir, exist_ok=True)
                with open(os.path.join(dest_dir, "SOURCE.md"), "w",
                          encoding="utf-8") as sf:
                    sf.write(f"# {d['title']}\n\n"
                             f"- 作者：{d['author'] or '未标注'}\n"
                             f"- 协议：{d['license']}\n"
                             f"- 来源：{d['url']}\n"
                             f"- 抓取日期：{time.strftime('%Y-%m-%d')}\n\n"
                             f"## 文件\n\n" +
                             "\n".join(f"- {os.path.basename(urllib.parse.unquote(f))}"
                                       for f in d["files"]) + "\n")
            except OSError as e:
                print(f"  SOURCE.md 写入失败: {e}", file=sys.stderr)
        print(f"[{i}/{len(seen)}] {d['title'][:48]!r} "
              f"{d['license']} {len(d['files'])}个 {d.get('bytes', 0)//1024}KB",
              file=sys.stderr)
        time.sleep(0.7)

    json.dump(rows, open(outjson, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"写入 {len(rows)} 条 -> {outjson}", file=sys.stderr)


if __name__ == "__main__":
    main()