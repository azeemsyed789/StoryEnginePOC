import os
import cv2
import base64
import requests
import uuid
from PIL import Image
from dotenv import load_dotenv
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import google.generativeai as genai
import insightface # Ensure this is imported for the swapper

# --- IDENTITY ENGINE SETUP ---
INSIGHTFACE_AVAILABLE = True 
face_app = None
swapper = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
OUTPUT_DIR = BASE_DIR / "static" / "generated"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# This is your live public address
PUBLIC_URL = "https://storyenginepoc.onrender.com"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


class StoryEngine:
    def __init__(self):
        self.previous_image_path = None 

    def encode_image_to_base64(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            return None

    def perform_identity_swap(self, scene_path, user_face_filename):
        global face_app, swapper 
        
        if not INSIGHTFACE_AVAILABLE:
            return str(scene_path)

        try:
            if face_app is None:
                from insightface.app import FaceAnalysis
                face_app = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
                face_app.prepare(ctx_id=0, det_size=(640, 640))

            if swapper is None:
                if os.path.exists("inswapper_128.onnx"):
                    swapper = insightface.model_zoo.get_model(
                        "inswapper_128.onnx", download=False, download_zip=False
                    )
                else:
                    return str(scene_path)
        except Exception as e:
            return str(scene_path)

        img = cv2.imread(str(scene_path))
        user_path = UPLOAD_DIR / user_face_filename
        source_img = cv2.imread(str(user_path))

        if img is None or source_img is None:
            return str(scene_path)

        try:
            source_faces = face_app.get(source_img)
            target_faces = face_app.get(img)
            
            if not source_faces or not target_faces:
                return str(scene_path)

            source_face = max(source_faces, key=lambda x: x.bbox[2] * x.bbox[3])
            target_face = max(target_faces, key=lambda x: x.bbox[2] * x.bbox[3])

            res = swapper.get(img, target_face, source_face, paste_back=True)
            out_filename = f"swap_{uuid.uuid4()}.png"
            out_path = OUTPUT_DIR / out_filename
            cv2.imwrite(str(out_path), res)
            return str(out_path)
        except Exception as e:
            return str(scene_path)

    def generate_page_image(self, page_config, user_face_filename, locked_style=None, primary_pose=None, secondary_pose=None):
        bg_filename = getattr(page_config, "background_filename", None)
        if not bg_filename: return "", ""
        
        bg_path = UPLOAD_DIR / bg_filename
        if not bg_path.exists(): return "", ""

        bg_image = Image.open(str(bg_path))
        character_specs = []
        has_placeholder = False
        secondary_char_count = 0
        
        for el in getattr(page_config, "elements", []):
            x_val = getattr(el, "x", 0.5)
            y_val = getattr(el, "y", 0.5)
            pose = getattr(el, "pose", "standing")
            char_type = getattr(el, "type", "")
            
            x_percent = int(x_val * 100)
            y_percent = int(y_val * 100)
            
            if char_type == "placeholder":
                has_placeholder = True
                user_image_path = UPLOAD_DIR / user_face_filename
                if user_image_path.exists():
                    character_specs.append({
                        "type": "main",
                        "image_path": user_image_path,
                        "x_percent": x_percent,
                        "y_percent": y_percent,
                        "pose": pose,
                        "identifier": "PRIMARY_MAIN"
                    })
            else:
                asset_filename = getattr(el, "asset_filename", None)
                if asset_filename:
                    asset_path = UPLOAD_DIR / asset_filename
                    if asset_path.exists():
                        secondary_char_count += 1
                        character_specs.append({
                            "type": "secondary",
                            "image_path": asset_path,
                            "x_percent": x_percent,
                            "y_percent": y_percent,
                            "pose": pose,
                            "identifier": f"SECONDARY_{secondary_char_count}"
                        })

        movement_instruction = f"PRIMARY CHARACTER: {primary_pose}. SECONDARY CHARACTER: {secondary_pose}."
        char_prompts = [f"- [{s['identifier']}] {'PRIMARY' if s['type']=='main' else 'SECONDARY'}: POS [X={s['x_percent']}%, Y={s['y_percent']}%]. POSE: {s['pose']}." for s in character_specs]

        final_prompt = f"COMPOSITION:\n{chr(10).join(char_prompts)}\nMOVEMENT: {movement_instruction}"
        if locked_style: final_prompt += f"\nSTYLE: {locked_style}"

        try:
            model = genai.GenerativeModel('gemini-1.5-pro') # Using stable model
            content = [final_prompt, bg_image]
            for spec in character_specs:
                char_img = Image.open(str(spec["image_path"]))
                char_img.thumbnail((1024, 1024))
                content.append(char_img)
            
            response = model.generate_content(content)
            img_bytes = next((part.inline_data.data for part in response.parts if hasattr(part, 'inline_data')), None)
            if not img_bytes: return "", ""
            
            temp_filename = f"gen_{uuid.uuid4()}.png"
            temp_path = OUTPUT_DIR / temp_filename
            with open(temp_path, "wb") as f: f.write(img_bytes)
            
            final_path = str(temp_path)
            if has_placeholder and INSIGHTFACE_AVAILABLE:
                final_path = self.perform_identity_swap(temp_path, user_face_filename)
            
            # FIXED: Returning relative path to be combined with BASE_URL in frontend
            return f"/static/generated/{Path(final_path).name}", final_path

        except Exception as e:
            return "", ""

    def compile_pdf(self, pages_data):
        from reportlab.lib.units import inch
        pdf_name = f"Story_{uuid.uuid4()}.pdf"
        pdf_path = OUTPUT_DIR / pdf_name
        page_width, page_height = 11 * inch, 8.5 * inch
        
        c = canvas.Canvas(str(pdf_path), pagesize=(page_width, page_height))
        
        for page in pages_data:
            img_p = page.get("image_path")
            if img_p and os.path.exists(img_p):
                c.drawImage(img_p, 20, 100, width=page_width-40, height=page_height-140, preserveAspectRatio=True)
            
            c.setFont("Helvetica", 12)
            c.drawString(20, 30, f"Story: {page.get('text', '')[:100]}")
            c.showPage()
        
        c.save()
        # FIXED: Returning the full PUBLIC Render URL for the PDF
        return f"{PUBLIC_URL}/static/generated/{pdf_name}"

    def analyze_generated_style(self, image_path):
        return "Cinematic photorealistic style"
