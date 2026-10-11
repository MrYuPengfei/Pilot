"""APNG（动画 PNG）解码器：纯 Python 实现，零第三方依赖。

为什么自己写：Qt 的 ``QMovie`` 只支持 gif/webp，``QImageReader`` 的内置格式里
也没有 apng（实测 PySide6 6.x）。而本项目运行时依赖只有 PySide6 + pygame-ce，
为看动画额外引入 Pillow 会加重 PyInstaller 打包体积，故用标准库
（``struct`` + ``zlib``）自行解码。

APNG 规范（PNG 扩展，见 W3C PNG 规范附录）关键点：

* ``acTL``  动画控制块，声明总帧数 num_frames 与循环次数 num_plays。
* ``fcTL``  帧控制块，逐帧声明 宽/高/偏移/延迟/合成方式/处置方式。
  **若fcTL 出现在 IDAT 之前，则该帧就是 PNG 的默认图**（第 0 帧）。
* ``fdAT``帧数据块，等同 IDAT 但**多一个 4 字节序号前缀**。

帧的延迟 = ``delay_num / delay_den`` 秒，其中 ``delay_den`` 为 0 时按 100 处理
（规范规定）。本模块统一换算成**毫秒**。

渲染一帧需要处理：

* ``blend_op``：0=SOURCE（整块替换）、1=OVER（按 alpha 混合）。
* ``dispose_op``：0=NONE（保留）、1=BACKGROUND（清回透明）、
  2=PREVIOUS（恢复上一帧）。不处理会得到残影/错位画面。

本模块输出**完整的 RGBA8 PNG 字节流**（每帧已合成到全画布），
交给 :class:`QPixmap` 直接 ``loadFromData`` 即可。
"""

import struct
import zlib

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

# fcTL 字段：seq, w, h, x_offset, y_offset, delay_num, delay_den, dispose_op, blend_op
_FCTL = struct.Struct('>IIIIIHHBB')
_ACTL = struct.Struct('>II')
_IHDR = struct.Struct('>IIBBBBB')

# 处置方式 / 混合方式常量（规范里的语义名更好读）
DISPOSE_NONE = 0
DISPOSE_BACKGROUND = 1
DISPOSE_PREVIOUS = 2
BLEND_SOURCE = 0
BLEND_OVER = 1

# 每行 1 像素的字节数：按颜色类型 + 位深
_BYTES_PER_PIXEL = {
    (0, 1): 1, (0, 2): 1, (0, 4): 1, (0, 8): 1, (0, 16): 2,   # 灰度
    (2, 8): 3, (2, 16): 6,                                        # 真彩
    (3, 1): 1, (3, 2): 1, (3, 4): 2, (3, 8): 1, (3, 16): 2,       # 索引
    (4, 8): 2, (4, 16): 4,                                        # 灰度+alpha
    (6, 8): 4, (6, 16): 8,                                        # 真彩+alpha
}


class ApngError(ValueError):
    """APNG 数据不合法。"""


class ApngFrame:
    """解码后的一帧。``data`` 是可直接给 Qt 用的完整 PNG 字节流。"""

    __slots__ = ('index', 'png', 'duration_ms', 'width', 'height')

    def __init__(self, index, png, duration_ms, width, height):
        self.index = index
        self.png = png
        self.duration_ms = duration_ms
        self.width = width
        self.height = height

    def __repr__(self):
        return (f'ApngFrame(#{self.index} {self.width}x{self.height} '
                f'{self.duration_ms}ms {len(self.png)}B)')


def _iter_chunks(data):
    """遍历 PNG chunk，产出 (类型, 数据体)。遇到 IEND 或数据截断即停止。"""
    if not data.startswith(PNG_SIGNATURE):
        raise ApngError('不是 PNG 文件（签名不匹配）')
    i = len(PNG_SIGNATURE)
    n = len(data)
    while i + 8 <= n:
        (length,) = struct.unpack('>I', data[i:i + 4])
        ctype = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + length]
        if len(body) < length:
            raise ApngError(f'chunk {ctype!r} 数据不完整')
        yield ctype, body
        i += 12 + length          # 4 长度 + 4 类型 + 数据 + 4 CRC
        if ctype == b'IEND':
            return


def is_apng(data):
    """判断字节流是否为 APNG（含 acTL 且至少一帧）。"""
    if not data.startswith(PNG_SIGNATURE):
        return False
    has_actl = False
    try:
        for ctype, _ in _iter_chunks(data):
            if ctype == b'acTL':
                has_actl = True
            elif ctype == b'fcTL' and has_actl:
                # acTL 与 fcTL 都出现才算 APNG（fcTL 在 acTL 之后才合法）
                return True
    except ApngError:
        return False
    return False


def _paeth(a, b, c):
    """PNG Paeth 预测器（APNG 与 PNG 共用）。"""
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw, width, height, bpp):
    """按 PNG 滤波器还原像素数据，返回逐行字节（bytes 列表）。

    滤波是**行内串行依赖**（Sub/Average/Paeth 都要看左邻），无法向量化。
    曾尝试把整行当大整数一次相加以提速，但字节间会产生**进位串扰**
    （实测在非字节边界处错位），正确性优先，故保留朴素的逐字节实现。
    桌宠素材单帧 ≤300px，实测每帧约 20–30ms，够用。
    """
    stride = width * bpp
    out = []
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        if len(line) < stride:
            raise ApngError('扫描线数据不足')
        pos += stride
        if ftype == 0:
            pass
        elif ftype == 1:                      # Sub
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:                      # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:                      # Average
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:                      # Paeth
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                upleft = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
        else:
            raise ApngError(f'未知的 PNG 滤波器类型: {ftype}')
        out.append(bytes(line))
        prev = line
    return out


def _encode_png(width, height, rgba_rows):
    """把 RGBA8 像素行打包成PNG 字节流（每行前缀 filter type 0）。"""
    raw = bytearray()
    for row in rgba_rows:
        raw.append(0)                       # filter: None
        raw += row

    def chunk(ctype, body):
        return (struct.pack('>I', len(body)) + ctype + body
                + struct.pack('>I', zlib.crc32(ctype + body) & 0xFFFFFFFF))

    ihdr = _IHDR.pack(width, height, 8, 6, 0, 0, 0)   # 8bit RGBA
    return (PNG_SIGNATURE + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', zlib.compress(bytes(raw), 6))
            + chunk(b'IEND', b''))


def _blank(width, height):
    return [bytearray(width * 4) for _ in range(height)]


def _source_rect(canvas, sub_rows, sub_w, sub_h, x, y, blend_op):
    """把子帧按blend_op 合成到画布对应位置。"""
    cw = len(canvas[0]) // 4
    ch = len(canvas)
    for row_i in range(sub_h):
        cy = y + row_i
        if cy < 0 or cy >= ch:
            continue
        dst = canvas[cy]
        src = sub_rows[row_i]
        for px in range(sub_w):
            cx = x + px
            if cx < 0 or cx >= cw:
                continue
            di = cx * 4
            sa = src[px * 4 + 3]
            if blend_op == BLEND_SOURCE or sa == 255:
                dst[di:di + 4] = src[px * 4:px * 4 + 4]
            elif sa == 0:
                pass                      # 完全透明，覆盖后仍是原样
            else:
                # OVER：src 在上、dst 在下
                da = dst[di + 3]
                oa = sa + da * (255 - sa) // 255
                if oa == 0:
                    dst[di:di + 4] = b'\x00\x00\x00\x00'
                    continue
                for c in range(3):
                    sc = src[px * 4 + c]
                    dc = dst[di + c]
                    dst[di + c] = (sc * sa + dc * da * (255 - sa) // 255) // oa
                dst[di + 3] = oa


def _decode_raw_frame(idat, width, height, color_type, bit_depth):
    """把 IDAT/fdAT 数据解码成 RGBA8 像素行。"""
    bpp_bits = (color_type, bit_depth)
    if bpp_bits not in _BYTES_PER_PIXEL:
        raise ApngError(f'暂不支持的颜色类型/位深: {color_type}/{bit_depth}')
    bpp = _BYTES_PER_PIXEL[bpp_bits]
    if bit_depth != 8:
        # 桌面伙伴素材都是 8bit；更低/更高位深交给 Qt 直接解整帧（走回退路径）
        raise ApngError(f'暂不支持的位深: {bit_depth}')
    raw = zlib.decompress(idat)
    rows = _unfilter(raw, width, height, bpp)

    if color_type == 6:                    # RGBA
        return rows
    if color_type == 2:                    # RGB -> 补 alpha
        return [bytearray(_add_alpha(r)) for r in rows]
    if color_type == 0:                    # 灰度 -> RGB + alpha
        return [bytearray(_gray_to_rgba(r)) for r in rows]
    if color_type == 4:                    # 灰度+alpha
        return [bytearray(_ga_to_rgba(r)) for r in rows]
    raise ApngError(f'需调色板才能解码的颜色类型: {color_type}')


def _add_alpha(row):
    out = bytearray(len(row) * 4 // 3)
    for i in range(0, len(row), 3):
        out[i * 4 // 3:i * 4 // 3 + 3] = row[i:i + 3]
        out[i * 4 // 3 + 3] = 255
    return out


def _gray_to_rgba(row):
    out = bytearray(len(row) * 4)
    for i, g in enumerate(row):
        out[i * 4:i * 4 + 3] = bytes((g, g, g))
        out[i * 4 + 3] = 255
    return out


def _ga_to_rgba(row):
    out = bytearray(len(row) * 2)
    for i in range(0, len(row), 2):
        g, a = row[i], row[i + 1]
        out[i * 2:i * 2 + 3] = bytes((g, g, g))
        out[i * 2 + 3] = a
    return out


def probe(data):
    """只读解析头部，返回 (宽, 高, 帧数, 循环次数, 各帧时长ms)。

   不解码像素，因此很快——用来在管理面板展示素材信息、或在渲染前判断合法性。
    """
    width = height = None
    color_type = bit_depth = None
    total = 0
    plays = 0
    durations = []
    for ctype, body in _iter_chunks(data):
        if ctype == b'IHDR':
            width, height, bit_depth, color_type = _IHDR.unpack(body)[:4]
        elif ctype == b'acTL':
            total, plays = _ACTL.unpack(body[:8])
        elif ctype == b'fcTL':
            seq, w, h, x, y, dnum, dden, dop, bop = _FCTL.unpack(body)
            durations.append(_duration_ms(dnum, dden))
    return width, height, total or len(durations), plays, durations


def _duration_ms(dnum, dden):
    """delay_num / delay_den 秒 -> 毫秒。den 为 0 视为 100（规范规定）。"""
    den = dden or 100
    ms = round(dnum * 1000 / den)
    # 0 毫秒会让 QTimer 变成忙循环；钳一个下限
    return max(ms, 10)


def _idat_precedes_fctl(data):
    """判断 IDAT 是否出现在首个 fcTL **之前**。

    返回 True 表示「fcTL 在 IDAT 之后」，即 IDAT 只是一张独立的静态预览图，
    **不属于任何一帧**；返回 False 表示「fcTL 在 IDAT 之前」，
    此时第一个 fcTL 描述的就是这张默认图，其数据来自 IDAT。

    APNG 规范把两种布局都视为合法：大量导出工具（如本项目素材所用的 Lottie→PNG
    流水线）采用后者，即 ``acTL, fcTL, IDAT..., fcTL, fdAT...``；
    而「预览图在前、动画在后」的布局里 IDAT 会被重复计入第 0 帧，导致帧错位。
    """
    for ctype, _ in _iter_chunks(data):
        if ctype == b'fcTL':
            return False
        if ctype == b'IDAT':
            return True
    return True


def decode(data, max_frames=None):
    """解码 APNG 为帧列表[:class:`ApngFrame`]。

    :param max_frames: 只取前N 帧（``animated.png`` 有 339 帧，全解会占用
        大量内存；桌宠通常只用得上几十帧）。``None`` 表示全部。
    """
    if not is_apng(data):
        raise ApngError('不是 APNG（缺少 acTL 或 fcTL）')

    # ---- 第一遍：按 fcTL 把 IDAT/fdAT 分配到各帧 ----
    #
    # 规范要点：fcTL 在 IDAT **之前**时，该帧就是 PNG 的默认图（用 IDAT 作数据）；
    # fcTL 在 IDAT **之后**时，IDAT 只是「预览用默认图」，**不属于任何一帧**。
    # 实测 Spinner 系列属于前者，fdAT 序列号与 fcTL 交错（0,1,3,5…），
    # 所以不能按「第N 个 fcTL 对应第N 个 fdAT」来猜，必须靠 fcTL 边界切分。
    ihdr = None
    frames_raw = []          # [{'ctl': fcTL 元组, 'idat': bytearray}]
    cur = None
    idat_chunks = []          # 收集所有 IDAT，等确认「是否为默认图帧」后再用

    for ctype, body in _iter_chunks(data):
        if ctype == b'IHDR':
            ihdr = body
        elif ctype == b'acTL':
            pass# 循环次数等信息在 probe() 里已取，这里不需要
        elif ctype == b'fcTL':
            ctl = _FCTL.unpack(body)
            cur = {'ctl': ctl, 'idat': bytearray()}
            frames_raw.append(cur)
        elif ctype == b'IDAT':
            idat_chunks.append(body)
        elif ctype == b'fdAT':
            if cur is None:
                raise ApngError('fdAT 出现在 fcTL 之前')
            cur['idat'] += body[4:]      # 跳过 4 字节序列号

    if not frames_raw:
        raise ApngError('没有可解码的帧')

    # IDAT 归属：只有「fcTL 出现在 IDAT 之前」时，IDAT 才是第 0 帧的数据。
    # 反之（预览图在前）IDAT 与动画无关，必须忽略，否则第 0 帧会混入静态预览内容。
    if idat_chunks and not _idat_precedes_fctl(data):
        frames_raw[0]['idat'] = bytearray(b''.join(idat_chunks))

    if ihdr is None:
        raise ApngError('缺少 IHDR')
    width, height, bit_depth, color_type = _IHDR.unpack(ihdr)[:4]
    if not frames_raw:
        raise ApngError('没有可解码的帧')

    if max_frames:
        frames_raw = frames_raw[:max_frames]

    # ---- 第二遍：逐帧合成到全画布 ----
    canvas = _blank(width, height)
    previous = None                 # dispose_op=PREVIOUS 时的快照
    out = []
    for idx, fr in enumerate(frames_raw):
        seq, fw, fh, fx, fy, dnum, dden, dop, bop = fr['ctl']
        if not fr['idat']:
            raise ApngError(f'第 {idx} 帧缺少像素数据')

        if dop == DISPOSE_PREVIOUS:
            previous = [bytearray(r) for r in canvas]
        elif dop == DISPOSE_BACKGROUND:
            previous = None

        sub_rows = _decode_raw_frame(bytes(fr['idat']), fw, fh,
                                     color_type, bit_depth)
        _source_rect(canvas, sub_rows, fw, fh, fx, fy, bop)

        out.append(ApngFrame(idx, _encode_png(width, height, canvas),
                             _duration_ms(dnum, dden), width, height))

        # 本帧显示完后，按 dispose_op 决定画布如何变化（影响下一帧）
        if dop == DISPOSE_BACKGROUND:
            for yy in range(fy, min(fy + fh, height)):
                if 0 <= yy < height:
                    xx0 = max(fx, 0)
                    xx1 = min(fx + fw, width)
                    if xx1 > xx0:
                        canvas[yy][xx0 * 4:xx1 * 4] = b'\x00' * ((xx1 - xx0) * 4)
        elif dop == DISPOSE_PREVIOUS and previous is not None:
            canvas = previous

    return out


def frame_count(data):
    """帧数（取 acTL 声明值；缺失时回退 fcTL 计数）。"""
    return probe(data)[2]