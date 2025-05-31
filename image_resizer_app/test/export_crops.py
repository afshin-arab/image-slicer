
import os
import hashlib
import random
from PIL import Image

def generate_filename(base, index, suffix, ext):
    hash_part = hashlib.sha256(str(random.random()).encode()).hexdigest()[:8]
    return f"{base}-{index}-{hash_part}{suffix}{ext}"

def export_crops(image_path, vertical_lines, horizontal_lines, output_dir, prefix="cropped", suffix="", ext=".jpg"):
    image = Image.open(image_path)
    image_width, image_height = image.size

    os.makedirs(output_dir, exist_ok=True)

    x_lines = [0] + sorted(vertical_lines) + [image_width]
    y_lines = [0] + sorted(horizontal_lines) + [image_height]

    crop_index = 1
    for i in range(len(x_lines) - 1):
        for j in range(len(y_lines) - 1):
            x1, x2 = x_lines[i], x_lines[i + 1]
            y1, y2 = y_lines[j], y_lines[j + 1]
            cropped = image.crop((x1, y1, x2, y2))
            filename = generate_filename(prefix, crop_index, suffix, ext)
            cropped.save(os.path.join(output_dir, filename))
            crop_index += 1

    print(f"Exported {crop_index - 1} cropped images to: {output_dir}")

# Example usage (you can delete or replace this with your app call):
if __name__ == "__main__":
    export_crops(
        image_path="sample_image.jpg",
        vertical_lines=[200, 400, 600],
        horizontal_lines=[150, 450],
        output_dir="exports"
    )
