#!/usr/bin/env python3
"""
水印替换程序 v2.0
────────────────────────────────────────────────────────────────
功能：自动将"清华同方 / 同方股份有限公司"水印替换为
      "同方泰德 / 同方泰德国际科技（北京）有限公司"

依赖：pip install Pillow numpy

用法：
  单张：  python watermark_replacer.py photo.jpg
  批量：  python watermark_replacer.py *.jpg
  指定目录：python watermark_replacer.py *.jpg -o ./output
  自定义后缀：python watermark_replacer.py *.jpg --suffix _v2
  自定义资源：python watermark_replacer.py *.jpg --logo my_logo.png --bar my_bar.jpg

目录结构：
  watermark_replacer.py       ← 本脚本
  logo_tongfangtaider.png     ← 同方泰德 Logo
  bar_tongfangtaider.jpg      ← 底部蓝色维保单位栏
────────────────────────────────────────────────────────────────
"""

import sys, os, glob, argparse
import numpy as np
from PIL import Image

# ── 资源文件默认路径（与脚本同目录）──────────────────────────────
_DIR        = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOGO = os.path.join(_DIR, "logo_tongfangtaider.png")
DEFAULT_BAR  = os.path.join(_DIR, "bar_tongfangtaider.jpg")


# ════════════════════════════════════════════════════════════════
# 自动检测
# ════════════════════════════════════════════════════════════════

def find_logo_box(arr, w, h):
    """
    检测白色 logo 方框（圆角卡片左侧白色区域）。
    返回 (x1, y1, x2, y2) 或 None。
    """
    best_run = None

    for x_probe in [50, 80, 100, 130]:
        if x_probe >= w:
            continue
        whites = [
            y for y in range(int(0.50 * h), int(0.90 * h))
            if arr[y, x_probe, 0] > 215
            and arr[y, x_probe, 1] > 215
            and arr[y, x_probe, 2] > 215
        ]
        if not whites:
            continue
        # 找最长连续段
        runs, s = [], whites[0]
        for i in range(1, len(whites)):
            if whites[i] - whites[i - 1] > 25:
                runs.append((s, whites[i - 1]))
                s = whites[i]
        runs.append((s, whites[-1]))
        run = max(runs, key=lambda r: r[1] - r[0])
        if run[1] - run[0] < h * 0.04:
            continue
        if best_run is None or (run[1] - run[0]) > (best_run[1] - best_run[0]):
            best_run = run

    if best_run is None:
        return None

    y1, y2 = best_run

    # 向下延伸：覆盖白色框圆角 + 可能溢出的英文小字
    x_check = 60
    for y in range(y2, min(y2 + 250, h)):
        r, g, b = int(arr[y, x_check, 0]), int(arr[y, x_check, 1]), int(arr[y, x_check, 2])
        if r > 225 and g > 225 and b > 225:
            y2 = y   # 白色仍在延伸
        else:
            break
    # 再多盖几行确保英文字完全消除
    y2 = min(y2 + 15, h - 1)

    # 水平边界（在 y 中点处扫描）
    y_mid = (y1 + y2) // 2
    x1 = 0
    for x in range(0, w // 3):
        r, g, b = int(arr[y_mid, x, 0]), int(arr[y_mid, x, 1]), int(arr[y_mid, x, 2])
        if r > 215 and g > 215 and b > 215:
            x1 = x
            break

    # 右边界：蓝色区域起点
    x2 = int(0.22 * w)
    for x in range(x1 + 10, w // 2):
        r, g, b = int(arr[y_mid, x, 0]), int(arr[y_mid, x, 1]), int(arr[y_mid, x, 2])
        if int(b) - int(r) > 45:
            x2 = x
            break

    return (x1, y1, x2, y2)


def find_blue_bar(arr, w, h):
    """
    检测底部蓝色"维保单位"栏。
    返回 (x1, y1, x2, y2) 或 None。
    x1 与 logo 框左边对齐（圆角卡片左边界）。
    """
    blue_rows = set()
    for x_probe in [100, 200, 300, 400]:
        if x_probe >= w:
            continue
        for y in range(int(0.85 * h), h):
            r, g, b = int(arr[y, x_probe, 0]), int(arr[y, x_probe, 1]), int(arr[y, x_probe, 2])
            if int(b) - int(r) > 40:
                blue_rows.add(y)

    if not blue_rows:
        return None

    y1, y2 = min(blue_rows), max(blue_rows)
    y_mid = (y1 + y2) // 2

    # 右边界
    x2 = w // 2
    for x in range(w - 1, 0, -1):
        r, g, b = int(arr[y_mid, x, 0]), int(arr[y_mid, x, 1]), int(arr[y_mid, x, 2])
        if int(b) - int(r) > 40:
            x2 = x + 1
            break

    # 左边界（与卡片圆角左边对齐）
    x1 = 0
    for x in range(0, w // 4):
        r, g, b = int(arr[y_mid, x, 0]), int(arr[y_mid, x, 1]), int(arr[y_mid, x, 2])
        if int(b) - int(r) > 40:
            x1 = x
            break

    return (x1, y1, x2, y2)


# ════════════════════════════════════════════════════════════════
# 替换操作
# ════════════════════════════════════════════════════════════════

def replace_logo(img, logo_box, logo_img):
    """用新 logo 填充白色 logo 框（居中、带内边距）。"""
    x1, y1, x2, y2 = logo_box
    box_w, box_h = x2 - x1, y2 - y1

    bg = Image.new("RGB", (box_w, box_h), (248, 248, 248))
    scale = min(box_w / logo_img.width, box_h / logo_img.height) * 0.85
    nw = max(1, int(logo_img.width  * scale))
    nh = max(1, int(logo_img.height * scale))
    scaled = logo_img.resize((nw, nh), Image.LANCZOS)
    bg.paste(scaled, ((box_w - nw) // 2, (box_h - nh) // 2))

    out = img.copy()
    out.paste(bg, (x1, y1))
    return out


def replace_blue_bar(img, bar_box, bar_img):
    """将蓝色底栏替换为新底栏图（直接缩放贴图，保持左边对齐）。"""
    x1, y1, x2, y2 = bar_box
    bar_w, bar_h = x2 - x1, y2 - y1

    bar_resized = bar_img.resize((bar_w, bar_h), Image.LANCZOS)
    out = img.copy()
    out.paste(bar_resized, (x1, y1))
    return out


# ════════════════════════════════════════════════════════════════
# 单图处理
# ════════════════════════════════════════════════════════════════

def process_image(input_path, output_path, logo_img, bar_img):
    """处理单张图片，返回 True 表示成功。"""
    try:
        img = Image.open(input_path).convert("RGB")
        arr = np.array(img)
        w, h = img.size
        print(f"  尺寸: {w}×{h}")

        # 检测 logo 框
        logo_box = find_logo_box(arr, w, h)
        if logo_box is None:
            print("  ⚠ 未检测到白色 logo 框，跳过")
            return False
        print(f"  Logo框: ({logo_box[0]},{logo_box[1]})-({logo_box[2]},{logo_box[3]})")

        # 检测蓝色底栏
        blue_bar = find_blue_bar(arr, w, h)
        if blue_bar is None:
            print("  ⚠ 未检测到蓝色底栏，跳过")
            return False
        print(f"  蓝色栏: ({blue_bar[0]},{blue_bar[1]})-({blue_bar[2]},{blue_bar[3]})")

        # 替换
        img = replace_logo(img, logo_box, logo_img)
        img = replace_blue_bar(img, blue_bar, bar_img)

        # 保存
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, quality=95)
        print(f"  ✓ 已保存: {output_path}")
        return True

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False


# ════════════════════════════════════════════════════════════════
# 入口
# ════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="同方泰德水印替换工具 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python watermark_replacer.py photo.jpg
  python watermark_replacer.py *.jpg -o ./output
  python watermark_replacer.py *.jpg --suffix _new
  python watermark_replacer.py *.jpg --logo my_logo.png --bar my_bar.jpg
        """
    )
    parser.add_argument("inputs",       nargs="+",         help="输入图片（支持 *.jpg 通配符）")
    parser.add_argument("-o", "--output-dir", default=None, help="输出目录（默认在原文件旁）")
    parser.add_argument("--suffix",     default="_新水印",  help="输出文件名后缀（默认: _新水印）")
    parser.add_argument("--logo",       default=DEFAULT_LOGO, help="Logo 图片路径")
    parser.add_argument("--bar",        default=DEFAULT_BAR,  help="底栏图片路径")
    args = parser.parse_args()

    # 展开通配符
    EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    files = []
    for pattern in args.inputs:
        matched = glob.glob(pattern)
        files.extend(matched if matched else ([pattern] if os.path.isfile(pattern) else []))
    files = [f for f in files if os.path.splitext(f)[1].lower() in EXT]

    if not files:
        print("错误：没有找到有效的图片文件")
        sys.exit(1)

    # 检查资源文件
    for label, path in [("Logo", args.logo), ("底栏图", args.bar)]:
        if not os.path.exists(path):
            print(f"错误：{label} 文件不存在 → {path}")
            print("请将资源文件放在脚本同目录，或用 --logo / --bar 指定路径")
            sys.exit(1)

    logo_img = Image.open(args.logo).convert("RGB")
    bar_img  = Image.open(args.bar).convert("RGB")
    print(f"Logo : {logo_img.size[0]}×{logo_img.size[1]}  {args.logo}")
    print(f"底栏 : {bar_img.size[0]}×{bar_img.size[1]}   {args.bar}")
    print(f"共 {len(files)} 张图片待处理\n{'─'*40}")

    ok = fail = 0
    for i, src in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {os.path.basename(src)}")
        base, ext = os.path.splitext(src)
        if args.output_dir:
            dst = os.path.join(args.output_dir, os.path.basename(base) + args.suffix + ext)
        else:
            dst = base + args.suffix + ext

        if process_image(src, dst, logo_img, bar_img):
            ok += 1
        else:
            fail += 1

    print(f"{'─'*40}\n完成：成功 {ok} 张，失败 {fail} 张")


if __name__ == "__main__":
    main()
