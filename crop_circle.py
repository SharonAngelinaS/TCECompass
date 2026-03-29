import os
from PIL import Image, ImageDraw

input_path = r"e:\CHANGED DOWNLOAD FOLDER\TCE-Compass-Integrated\TCE-Compass-Integrated\frontend\public\logo.jpg"
output_path = r"e:\CHANGED DOWNLOAD FOLDER\TCE-Compass-Integrated\TCE-Compass-Integrated\frontend\public\logo.png"

try:
    img = Image.open(input_path).convert("RGBA")
    
    min_dim = min(img.size)
    left = (img.width - min_dim) / 2
    top = (img.height - min_dim) / 2
    right = (img.width + min_dim) / 2
    bottom = (img.height + min_dim) / 2
    img = img.crop((left, top, right, bottom))
    
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
    
    img.putalpha(mask)
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    img.save(output_path, "PNG")
    print("SUCCESS")
except Exception as e:
    print("ERROR:", e)
