from PIL import Image, ImageDraw, ImageFont
import os
import config

def add_watermark(input_image_path, output_image_path):
    """Накладывает водяной знак (по центру справа, без прозрачности)."""
    try:
        base_image = Image.open(input_image_path).convert("RGBA")
        width, height = base_image.size

        overlay = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        text = config.WATERMARK_TEXT

        # Размер шрифта (4% от высоты картинки)
        font_size = int(height * 0.04)
        if font_size < 20: font_size = 25
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
            print("⚠️ Шрифт arial.ttf не найден, использую стандартный.")

        # Вычисляем размер текста
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Координаты: отступ справа 40 пикселей, по высоте - ровно по центру
        x = width - text_width - 40
        y = int(height / 2)

        # Рисуем: цвет белый, альфа 255 (полностью непрозрачный)
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        watermarked = Image.alpha_composite(base_image, overlay)
        watermarked = watermarked.convert("RGB")
        watermarked.save(output_image_path, "JPEG", quality=95)
        return True

    except Exception as e:
        print(f"❌ Ошибка наложения водяного знака: {e}")
        return False