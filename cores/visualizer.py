import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import logging

class Visualizer:
    
    def __init__(self, config: dict):
        self.logger = logging.getLogger("AIPipeline")
        self.font_path = config.get('system', {}).get('font_path', 'fonts/tahoma.ttf')
        
        self.fonts = {}

    def _get_font(self, size):

        if size not in self.fonts:
            try:
                self.fonts[size] = ImageFont.truetype(self.font_path, size)
                self.logger.debug(f"[Visualizer] Loaded font {self.font_path} (Size: {size})")
            except IOError:
                self.logger.warning(f"[Visualizer] Font not found at {self.font_path}. Using default.")
                self.fonts[size] = ImageFont.load_default()
        return self.fonts[size]

    def draw_unicode_text(self, img_bgr, text, position, font_size=32, color=(0, 255, 0)):
        
        font = self._get_font(font_size)
        
       
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
    
        b, g, r = color
        draw.text(position, text, font=font, fill=(r, g, b))
        
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)