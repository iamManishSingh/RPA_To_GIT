from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import requests
from io import BytesIO
import textwrap

class FlyerGenerator:
    def __init__(self, text_plan, image_plan):
        self.text_plan = text_plan
        self.image_plan = image_plan
        self.width, self.height = 1200, 1600  # Standard flyer size
        
    def _create_gradient_background(self):
        """Create a modern gradient background"""
        base = Image.new('RGB', (self.width, self.height), '#FFFFFF')
        top_color = self._hex_to_rgb('#FFEECC')
        bottom_color = self._hex_to_rgb('#2A2A2A')
        
        for y in range(self.height):
            r = top_color[0] + (bottom_color[0] - top_color[0]) * y // self.height
            g = top_color[1] + (bottom_color[1] - top_color[1]) * y // self.height
            b = top_color[2] + (bottom_color[2] - top_color[2]) * y // self.height
            draw = ImageDraw.Draw(base)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return base

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _load_image(self):
        """Load and process main image"""
        try:
            response = requests.get(self.image_plan.image_url)
            img = Image.open(BytesIO(response.content))
            
            # Create circular mask
            mask = Image.new('L', img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
            
            # Apply mask and resize
            img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
            img.putalpha(mask)
            
            return img.resize((600, 600))  # Size for circular image
            
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    def _add_text(self, draw, y_position, text, font_size, font_name, color, max_width, is_title=False):
        """Smart text placement with wrapping and effects"""
        try:
            font = ImageFont.truetype(font_name, font_size)
        except:
            font = ImageFont.load_default(font_size)
            
        wrapped_text = textwrap.wrap(text, width=20 if is_title else 30)
        text_height = 0
        
        for line in wrapped_text:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2 if is_title else (self.width//2 + 50)
            
            # Text shadow effect
            if 'shadow' in self.text_plan.text_effects:
                draw.text((x+2, y_position+2), line, font=font, fill='#00000088')
                
            # Gradient text effect
            if 'gradient' in self.text_plan.text_effects:
                for i, char in enumerate(line):
                    ratio = i/len(line)
                    r = int(color[0] * (1 - ratio) + 255 * ratio)
                    g = int(color[1] * (1 - ratio) + 215 * ratio)
                    b = int(color[2] * (1 - ratio) + 0 * ratio)
                    draw.text((x + i*font_size*0.6, y_position), char, 
                             font=font, fill=(r, g, b))
            else:
                draw.text((x, y_position), line, font=font, fill=color)
            
            text_height += font_size + 10
            y_position += font_size + 10
            
        return y_position

    def _create_cta_button(self, draw):
        """Create modern CTA button"""
        button_text = self.text_plan.cta_button
        font_size = 40
        try:
            font = ImageFont.truetype(self.text_plan.font_style[0], font_size)
        except:
            font = ImageFont.load_default(font_size)
            
        bbox = draw.textbbox((0, 0), button_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Button dimensions
        button_width = text_width + 60
        button_height = text_height + 30
        x = (self.width - button_width) // 2
        y = self.height - 200
        
        # Button shape
        draw.rounded_rectangle(
            [x, y, x+button_width, y+button_height],
            radius=25,
            fill='#FF4444',  # Attention-grabbing red
            outline='#FFFFFF',
            width=3
        )
        
        # Button text
        draw.text(
            (x + (button_width - text_width)/2,
            y + (button_height - text_height)/2 - 5
        ), button_text, font=font, fill='#FFFFFF')
        
    def generate_flyer(self):
        """Main flyer generation method"""
        flyer = self._create_gradient_background()
        draw = ImageDraw.Draw(flyer)
        
        # Add shaped image
        image = self._load_image()
        if image:
            flyer.paste(image, (100, 300), image)
            
        # Add text elements
        y = 200
        primary_color = self._hex_to_rgb(self.text_plan.color_scheme)
        
        # Headline
        y = self._add_text(
            draw, y, self.text_plan.primary_headline,
            font_size=80,
            font_name=self.text_plan.font_style[0],
            color=primary_color,
            max_width=600,
            is_title=True
        )
        
        # Subtext
        y += 50
        self._add_text(
            draw, y, self.text_plan.subtext,
            font_size=40,
            font_name=self.text_plan.font_style[1],
            color=primary_color,
            max_width=500
        )
        
        # Add CTA button
        self._create_cta_button(draw)
        
        # Add decorative elements
        draw.rectangle([self.width//2 - 2, 150, self.width//2 + 2, self.height - 250],
                      fill='#FFFFFF55')
        
        # Save result
        flyer.save('modern_flyer.png', quality=95)
        return flyer

# Usage
text_plan = TextPlan(
    primary_headline="Summer Fashion Blowout!",
    subtext="Up to 70% Off Trendsetting Styles\nLimited Time Only!",
    font_style=["Montserrat-Bold.ttf", "OpenSans-Regular.ttf"],
    color_scheme="#2A2A2A",
    text_effects=["shadow", "gradient"],
    cta_button="SHOP NOW →"
)

image_plan = ImagePlan(
    image_url="https://example.com/fashion-image.jpg",
    # Other image parameters...
)

generator = FlyerGenerator(text_plan, image_plan)
result = generator.generate_flyer()
result.show()
