# 水印替换工具

自动将维保照片中的**清华同方**水印替换为**同方泰德**水印。

## 效果

| 替换前 | 替换后 |
|--------|--------|
| Logo：清华同方 | Logo：同方泰德 |
| 维保单位：同方股份有限公司 | 维保单位：同方泰德国际科技（北京）有限公司 |

## 文件说明

```
watermark_replacer.py      # 主程序
logo_tongfangtaider.png    # 同方泰德 Logo
bar_tongfangtaider.jpg     # 底部蓝色维保单位栏
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
# 处理单张图片
python watermark_replacer.py photo.jpg

# 批量处理当前目录所有 jpg
python watermark_replacer.py *.jpg

# 指定输出目录
python watermark_replacer.py *.jpg -o ./output

# 自定义输出文件名后缀（默认：_新水印）
python watermark_replacer.py *.jpg --suffix _v2

# 使用自定义 logo 或底栏图
python watermark_replacer.py *.jpg --logo my_logo.png --bar my_bar.jpg
```

## 输出示例

输入 `photo.jpg` → 输出 `photo_新水印.jpg`（原文件不变）

## 程序特性

- ✅ 自动检测 logo 白色框位置（适配不同分辨率）
- ✅ 自动检测底部蓝色维保单位栏位置
- ✅ 底栏左边界与水印卡片自动对齐
- ✅ 支持批量处理（`*.jpg`）
- ✅ 其余水印信息（区域、内容、责任人、时间）保持不变
- ✅ 支持 JPG / PNG / BMP / WEBP 格式

## 系统要求

- Python 3.7+
- Pillow
- numpy
