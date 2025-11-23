import os
import io
import base64
import textwrap
import re
import time
import traceback
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont, ImageFilter

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    print("⚠️ WARNING: No HF_TOKEN found.")

text_client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)
image_client = InferenceClient(model="stabilityai/stable-diffusion-xl-base-1.0", token=HF_TOKEN)

# --- HELPERS ---
def clean_text(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = text.replace('"', '').replace("'", "").strip()
    for prefix in ["Slogan:", "Here is a slogan:", "Answer:"]:
        if prefix in text: text = text.split(prefix)[-1].strip()
    return text

def enhance_image_prompt(business, desc, tone):
    base = f"A high-end commercial advertisement poster for {business} featuring {desc}."
    style = "High quality, 8k resolution, cinematic lighting."
    if "Catchy" in tone: style += " Vibrant colors, pop-art style, energetic."
    elif "Professional" in tone: style += " Sleek, minimalistic, modern office background."
    elif "Luxury" in tone: style += " Dark moody lighting, gold accents, elegant."
    elif "Humorous" in tone: style += " Playful, bright lighting, fun props."
    return f"{base} {style}"

# --- SMART LAYOUT ENGINE ---
def create_social_layout(img, business, slogan, format_type):
    # UPDATED: Larger Font Sizes
    try:
        title_font = ImageFont.truetype("font.ttf", 130) # Was 80
        slogan_font = ImageFont.truetype("font.ttf", 80) # Was 45
        small_font = ImageFont.truetype("font.ttf", 50)  # Was 30
    except:
        title_font = ImageFont.load_default()
        slogan_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    if format_type == "Story":
        # 9:16 Layout
        width, height = 1080, 1920
        canvas = Image.new('RGB', (width, height), (0,0,0))
        
        bg = img.resize((width + 200, height + 200))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
        left = (bg.width - width)/2
        top = (bg.height - height)/2
        bg = bg.crop((left, top, left + width, top + height))
        
        overlay = Image.new('RGBA', bg.size, (0,0,0,120)) # Slightly darker bg for contrast
        bg.paste(overlay, (0,0), overlay)
        canvas.paste(bg, (0,0))

        img_w, img_h = 900, 900
        main_img = img.resize((img_w, img_h))
        border = Image.new('RGB', (img_w+20, img_h+20), (255,255,255))
        canvas.paste(border, (90, 500)) 
        canvas.paste(main_img, (100, 510))

        draw = ImageDraw.Draw(canvas)
        
        # Title
        bbox = draw.textbbox((0, 0), business.upper(), font=title_font)
        text_width = bbox[2] - bbox[0]
        # Ensure title fits (if too wide, naive scaling isn't here, but centering works)
        draw.text(((width - text_width)/2, 200), business.upper(), font=title_font, fill="#FFD700")

        # Slogan (Wrapped tighter because font is huge)
        lines = textwrap.wrap(slogan, width=20) # Reduced width from 30 to 20
        y_text = 1500
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=slogan_font)
            line_width = bbox[2] - bbox[0]
            draw.text(((width - line_width)/2, y_text), line, font=slogan_font, fill="white")
            y_text += 90 # Increased line height spacing
            
        draw.text(((width - 300)/2, 1800), "^ SWIPE UP ^", font=small_font, fill="#cccccc")
        return canvas

    else:
        # Square Layout
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        # Bigger dark overlay to fit bigger text
        overlay = Image.new('RGBA', img.size, (0,0,0,0))
        d = ImageDraw.Draw(overlay)
        d.rectangle([(0, h - 300), (w, h)], fill=(0, 0, 0, 180)) # Taller box
        d.rectangle([(0, 0), (w, 180)], fill=(0, 0, 0, 150))     # Taller box
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        draw = ImageDraw.Draw(img)

        # Title
        bbox = draw.textbbox((0, 0), business.upper(), font=title_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((w - text_width) / 2, 30), business.upper(), font=title_font, fill="#FFD700")

        # Slogan
        lines = textwrap.wrap(slogan, width=25) # Reduced width from 40 to 25
        y_text = h - 250
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=slogan_font)
            line_width = bbox[2] - bbox[0]
            draw.text(((w - line_width) / 2, y_text), line, font=slogan_font, fill="white")
            y_text += 85
        return img

def draw_text_on_image(img, business_name, slogan):
    # Legacy function for 'Poster' mode, also updated
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    try:
        title_font = ImageFont.truetype("font.ttf", 130)
        slogan_font = ImageFont.truetype("font.ttf", 80)
    except:
        title_font = ImageFont.load_default()
        slogan_font = ImageFont.load_default()

    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, height - 300), (width, height)], fill=(0, 0, 0, 180))
    overlay_draw.rectangle([(0, 0), (width, 180)], fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), business_name.upper(), font=title_font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) / 2, 30), business_name.upper(), font=title_font, fill="#FFD700")

    lines = textwrap.wrap(slogan, width=25)
    y_text = height - 250
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=slogan_font)
        line_w = bbox[2] - bbox[0]
        draw.text(((width - line_w) / 2, y_text), line, font=slogan_font, fill="white")
        y_text += 85

    return img

def query_vision_api(img_bytes, token):
    model = "Salesforce/blip-image-captioning-base"
    api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, data=img_bytes)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', 'A product image')
            elif response.status_code == 503:
                time.sleep(2)
                continue
            else:
                print(f"Vision Fail: {response.status_code}")
                break
        except: break
    return None

# --- ROUTES ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "active", "message": "Desi-Scribe Backend is Live!"})

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    try:
        if 'file' not in request.files: return jsonify({"error": "No file"}), 400
        file = request.files['file']
        
        image = Image.open(file.stream).convert("RGB")
        image.thumbnail((512, 512)) 
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        caption = query_vision_api(img_bytes, HF_TOKEN)
        if not caption: caption = "A product image"

        guess_prompt = f"Based on: '{caption}', guess a short Business Name (max 3 words) and Tone. Format: Name | Tone"
        guess_res = text_client.chat_completion(messages=[{"role": "user", "content": guess_prompt}], max_tokens=50)
        guess_text = guess_res.choices[0].message.content.strip()
        
        if "|" in guess_text: name, tone = guess_text.split("|", 1)
        else: name, tone = "Auto Business", "Professional"

        return jsonify({"status": "success", "description": caption, "business_type": name.strip(), "tone": tone.strip()})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/generate-slogan', methods=['POST'])
def generate_slogan():
    try:
        data = request.get_json()
        lang = data.get('language', 'English')
        prompt = (f"Write a {data.get('ad_type')} slogan for {data.get('business_type')} "
                  f"({data.get('product_description')}) in {lang} language. Output ONLY the slogan.")
        res = text_client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=60)
        return jsonify({"status": "success", "slogan": clean_text(res.choices[0].message.content)})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/generate-poster', methods=['POST'])
def generate_poster():
    try:
        data = request.get_json()
        b_type = data.get('business_type')
        desc = data.get('product_description')
        tone = data.get('ad_type')
        lang = data.get('language', 'English')
        fmt = data.get('format', 'Square')

        # Slogan
        slogan_prompt = f"Write a catchy 5-word slogan for {b_type} in {lang} language."
        slogan_res = text_client.chat_completion(messages=[{"role": "user", "content": slogan_prompt}], max_tokens=40)
        slogan = clean_text(slogan_res.choices[0].message.content)

        # Image
        image_prompt = enhance_image_prompt(b_type, desc, tone)
        img = image_client.text_to_image(image_prompt)

        # Layout
        final_img = create_social_layout(img, b_type, slogan, fmt)

        buffered = io.BytesIO()
        final_img.convert('RGB').save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return jsonify({"status": "success", "image_url": f"data:image/jpeg;base64,{img_str}", "slogan": slogan})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
