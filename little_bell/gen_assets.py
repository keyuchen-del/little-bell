"""Generate menu bar icons and pet sprites for 小铃铛.
Pet design inspired by POP MART Dimoo / 星星人 style:
- 圆润大头身比例 (head:body ≈ 2:1)
- 星星造型耳朵/头饰
- 大大的圆眼睛 + 高光点
- 柔和马卡龙色系
- 微微嘟嘴 / 腮红
"""
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import math

ASSETS_DIR = Path(__file__).parent / "assets"

# 马卡龙配色
BODY_COLOR = "#B8E6F0"       # 薄荷蓝身体
BODY_SHADOW = "#8ECAD6"      # 身体阴影
CHEEK_COLOR = "#FFB3C6"      # 腮红粉
EYE_COLOR = "#2C2C2C"        # 眼睛
EYE_HIGHLIGHT = "#FFFFFF"    # 眼睛高光
STAR_COLOR = "#FFD93D"       # 星星金黄
STAR_OUTLINE = "#F5C518"     # 星星描边
BELL_COLOR = "#FFD93D"       # 铃铛
MOUTH_COLOR = "#E8788A"      # 小嘴

# Alert 配色
ALERT_BODY = "#FFB8D0"       # 告警时粉色身体
ALERT_SHADOW = "#E89AAF"
ALERT_STAR = "#FF6B6B"       # 告警星星变红


def draw_star(draw, cx, cy, r_outer, r_inner, points=5, fill=STAR_COLOR, outline=STAR_OUTLINE):
    """Draw a star shape."""
    coords = []
    for i in range(points * 2):
        angle = math.pi / 2 + i * math.pi / points
        r = r_outer if i % 2 == 0 else r_inner
        coords.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    draw.polygon(coords, fill=fill, outline=outline)


def draw_pet_idle(size, frame_idx):
    """Draw idle state pet - gentle floating animation."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    offsets_y = [0, -2, -3, -2]
    offset_y = offsets_y[frame_idx]

    cx, cy = size // 2, size // 2 + 5 + offset_y

    # Body - 圆润的蛋形身体
    body_w, body_h = 28, 22
    draw.ellipse(
        [cx - body_w, cy - body_h + 8, cx + body_w, cy + body_h + 8],
        fill=BODY_COLOR, outline=BODY_SHADOW, width=1
    )

    # Head - 大圆头 (比身体大)
    head_r = 24
    head_cy = cy - 14
    draw.ellipse(
        [cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
        fill=BODY_COLOR, outline=BODY_SHADOW, width=1
    )

    # 星星头饰 (左上方)
    star_x = cx - 10
    star_y = head_cy - head_r + 2
    draw_star(draw, star_x, star_y, 8, 4, fill=STAR_COLOR, outline=STAR_OUTLINE)

    # 小星星 (右上)
    draw_star(draw, cx + 14, head_cy - head_r + 6, 5, 2.5, fill=STAR_COLOR, outline=STAR_OUTLINE)

    # 眼睛 - 大圆眼 + 高光
    eye_y = head_cy + 2
    for ex in [cx - 9, cx + 9]:
        # 眼白/眼珠
        draw.ellipse([ex - 5, eye_y - 5, ex + 5, eye_y + 5], fill=EYE_COLOR)
        # 高光 (左上)
        draw.ellipse([ex - 3, eye_y - 3, ex, eye_y], fill=EYE_HIGHLIGHT)

    # 腮红
    draw.ellipse([cx - 20, eye_y + 4, cx - 13, eye_y + 9], fill=CHEEK_COLOR)
    draw.ellipse([cx + 13, eye_y + 4, cx + 20, eye_y + 9], fill=CHEEK_COLOR)

    # 小嘴 - 微笑弧线
    mouth_y = eye_y + 12
    draw.arc([cx - 4, mouth_y - 2, cx + 4, mouth_y + 4], 0, 180, fill=MOUTH_COLOR, width=2)

    # 铃铛 (挂在脖子上)
    bell_y = cy + 2
    draw.ellipse([cx - 4, bell_y, cx + 4, bell_y + 8], fill=BELL_COLOR, outline="#DAA520")
    draw.line([cx, bell_y + 4, cx, bell_y + 7], fill="#8B6914", width=1)

    # 小脚
    foot_y = cy + body_h + 5
    draw.ellipse([cx - 12, foot_y, cx - 4, foot_y + 6], fill=BODY_SHADOW)
    draw.ellipse([cx + 4, foot_y, cx + 12, foot_y + 6], fill=BODY_SHADOW)

    return img


def draw_pet_alert(size, frame_idx):
    """Draw alert state pet - shaking with surprised expression."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    offsets_x = [-3, 3, -2, 2]
    offset_x = offsets_x[frame_idx]

    cx, cy = size // 2 + offset_x, size // 2 + 5

    # Body
    body_w, body_h = 28, 22
    draw.ellipse(
        [cx - body_w, cy - body_h + 8, cx + body_w, cy + body_h + 8],
        fill=ALERT_BODY, outline=ALERT_SHADOW, width=1
    )

    # Head
    head_r = 24
    head_cy = cy - 14
    draw.ellipse(
        [cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
        fill=ALERT_BODY, outline=ALERT_SHADOW, width=1
    )

    # 星星头饰变红 (焦急)
    star_x = cx - 10
    star_y = head_cy - head_r + 2
    draw_star(draw, star_x, star_y, 9, 4.5, fill=ALERT_STAR, outline="#CC3333")
    draw_star(draw, cx + 14, head_cy - head_r + 6, 6, 3, fill=ALERT_STAR, outline="#CC3333")

    # 眼睛 - 惊讶大眼
    eye_y = head_cy + 2
    for ex in [cx - 9, cx + 9]:
        draw.ellipse([ex - 6, eye_y - 6, ex + 6, eye_y + 6], fill=EYE_COLOR)
        draw.ellipse([ex - 3, eye_y - 4, ex + 1, eye_y - 1], fill=EYE_HIGHLIGHT)

    # 腮红加深
    draw.ellipse([cx - 21, eye_y + 3, cx - 13, eye_y + 9], fill="#FF8FAB")
    draw.ellipse([cx + 13, eye_y + 3, cx + 21, eye_y + 9], fill="#FF8FAB")

    # 嘴巴 - 惊讶的O形
    mouth_y = eye_y + 12
    draw.ellipse([cx - 4, mouth_y - 1, cx + 4, mouth_y + 5], fill=MOUTH_COLOR)

    # 铃铛在摇晃
    bell_y = cy + 2
    bell_offset = [-2, 2, -1, 1][frame_idx]
    draw.ellipse([cx - 4 + bell_offset, bell_y, cx + 4 + bell_offset, bell_y + 8],
                 fill=BELL_COLOR, outline="#DAA520")

    # 感叹号 / 震动线
    draw.line([cx - head_r - 6, head_cy - 5, cx - head_r - 12, head_cy - 8], fill="#FF6B6B", width=2)
    draw.line([cx + head_r + 6, head_cy - 5, cx + head_r + 12, head_cy - 8], fill="#FF6B6B", width=2)
    draw.line([cx - head_r - 4, head_cy + 5, cx - head_r - 9, head_cy + 5], fill="#FF6B6B", width=2)
    draw.line([cx + head_r + 4, head_cy + 5, cx + head_r + 9, head_cy + 5], fill="#FF6B6B", width=2)

    # 小脚 (跳起)
    foot_y = cy + body_h + 3
    draw.ellipse([cx - 13, foot_y, cx - 5, foot_y + 6], fill=ALERT_SHADOW)
    draw.ellipse([cx + 5, foot_y, cx + 13, foot_y + 6], fill=ALERT_SHADOW)

    return img


def gen_menubar_icons():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Normal bell icon
    img = Image.new("RGBA", (22, 22), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([6, 4, 16, 14], fill="#555555")
    draw.rectangle([8, 13, 14, 16], fill="#555555")
    draw.ellipse([9, 16, 13, 20], fill="#555555")
    draw.arc([9, 1, 13, 5], 0, 180, fill="#555555", width=2)
    img.save(ASSETS_DIR / "bell.png")

    # Alert bell icon
    img = Image.new("RGBA", (22, 22), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([6, 4, 16, 14], fill="#FF3B30")
    draw.rectangle([8, 13, 14, 16], fill="#FF3B30")
    draw.ellipse([9, 16, 13, 20], fill="#FF3B30")
    draw.arc([9, 1, 13, 5], 0, 180, fill="#FF3B30", width=2)
    # Small star
    draw_star(draw, 18, 4, 4, 2, fill="#FFD93D", outline=None)
    img.save(ASSETS_DIR / "bell_alert.png")

    print(f"Generated menubar icons in {ASSETS_DIR}")


def gen_pet_sprites():
    pet_dir = ASSETS_DIR / "pet"
    pet_dir.mkdir(parents=True, exist_ok=True)

    size = 80

    for i in range(4):
        img = draw_pet_idle(size, i)
        img.save(pet_dir / f"idle_{i}.png")

    for i in range(4):
        img = draw_pet_alert(size, i)
        img.save(pet_dir / f"alert_{i}.png")

    print(f"Generated pet sprites in {pet_dir}")


if __name__ == "__main__":
    gen_menubar_icons()
    gen_pet_sprites()
