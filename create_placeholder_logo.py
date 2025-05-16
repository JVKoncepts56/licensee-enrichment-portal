import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

# Create a simple placeholder logo
def create_logo():
    # Create a white image
    width, height = 300, 120
    image = Image.new('RGBA', (width, height), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a blue rectangle
    draw.rectangle(
        [(20, 20), (280, 100)],
        fill=(0, 71, 171, 255),  # Cobalt Blue
        outline=(0, 71, 171, 255)
    )
    
    # Add text
    try:
        font = ImageFont.truetype("Arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    
    # Draw text
    draw.text(
        (40, 40),
        "LEP",
        fill=(255, 255, 255, 255),
        font=font
    )
    
    # Save the image
    image.save("logo.png")
    print("Placeholder logo created at 'logo.png'")

if __name__ == "__main__":
    create_logo()