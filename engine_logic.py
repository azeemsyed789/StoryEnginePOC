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

# --- IDENTITY ENGINE (LAZY LOADING SETUP) ---
print("--- IDENTITY ENGINE INITIALIZED (WAITING FOR CALL) ---")
INSIGHTFACE_AVAILABLE = True 
face_app = None
swapper = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
OUTPUT_DIR = BASE_DIR / "static" / "generated"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("⚠️ Warning: GOOGLE_API_KEY not set in .env file")
else:
    print(f"✅ Google API Key loaded: {GOOGLE_API_KEY[:20]}...")
    genai.configure(api_key=GOOGLE_API_KEY)


class StoryEngine:
    def __init__(self):
        self.previous_image_path = None  # Track previous image for reference

    def encode_image_to_base64(self, file_path: str) -> str:
        """Encode an image file to base64 string."""
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"⚠️ Error encoding image: {e}")
            return None

    def perform_identity_swap(self, scene_path, user_face_filename):
        global face_app, swapper 
        
        if not INSIGHTFACE_AVAILABLE:
            return str(scene_path)

        # --- LAZY LOADING LOGIC ---
        try:
            if face_app is None:
                print("📥 Loading FaceAnalysis (buffalo_s)...")
                from insightface.app import FaceAnalysis
                face_app = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
                face_app.prepare(ctx_id=0, det_size=(640, 640))

            if swapper is None:
                if os.path.exists("inswapper_128.onnx"):
                    print("📥 Loading Inswapper Model...")
                    swapper = insightface.model_zoo.get_model(
                        "inswapper_128.onnx", download=False, download_zip=False
                    )
                else:
                    print("❌ 'inswapper_128.onnx' missing. Skipping swap.")
                    return str(scene_path)
        except Exception as e:
            print(f"❌ Lazy Load Error: {e}")
            return str(scene_path)

        # --- ACTUAL SWAP LOGIC ---
        img = cv2.imread(str(scene_path))
        user_path = UPLOAD_DIR / user_face_filename
        source_img = cv2.imread(str(user_path))

        if img is None or source_img is None:
            return str(scene_path)

        try:
            source_faces = face_app.get(source_img)
            target_faces = face_app.get(img)
            
            if not source_faces or not target_faces:
                print("⚠️ No faces found for swapping.")
                return str(scene_path)

            source_face = max(source_faces, key=lambda x: x.bbox[2] * x.bbox[3])
            target_face = max(target_faces, key=lambda x: x.bbox[2] * x.bbox[3])

            res = swapper.get(img, target_face, source_face, paste_back=True)
            out_filename = f"swap_{uuid.uuid4()}.png"
            out_path = OUTPUT_DIR / out_filename
            cv2.imwrite(str(out_path), res)
            print("✅ Identity Injected.")
            return str(out_path)
        except Exception as e:
            print(f"⚠️ Swapper error: {e}")
            return str(scene_path)

    def generate_page_image(self, page_config, user_face_filename, locked_style=None, primary_pose=None, secondary_pose=None):
        print("🚀 Generating Page...")

        bg_filename = getattr(page_config, "background_filename", None)
        bg_path = None
        if bg_filename:
            bg_path = UPLOAD_DIR / bg_filename
            if not bg_path.exists():
                print(f"❌ Background image not found: {bg_filename}")
                return "", ""
        else:
            print("❌ No background image specified")
            return "", ""

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

        page_num = 1
        if self.previous_image_path:
            gen_files = list(OUTPUT_DIR.glob("gen_*.png"))
            page_num = min(len(gen_files) + 1, 5)
        
        if primary_pose and secondary_pose:
            movement_instruction = f"PRIMARY CHARACTER: {primary_pose}. SECONDARY CHARACTER: {secondary_pose}. Both characters should perform these exact movements together in synchronized action."
        else:
            movement_descriptions = {
                1: "BOTH CHARACTERS DANCING: Both primary and secondary characters are dancing together.",
                2: "BOTH CHARACTERS FIGHTING: Both primary and secondary characters in combat/fighting stances.",
                3: "BOTH CHARACTERS WALKING: Both primary and secondary characters walking together.",
                4: "BOTH CHARACTERS RUNNING TOWARDS EACH OTHER: High-energy rushing motion.",
                5: "BOTH CHARACTERS IN EPIC CONFRONTATION: Dramatic powerful movements."
            }
            movement_instruction = movement_descriptions.get(page_num, "Add dynamic synchronized movement.")

        char_prompts = []
        for spec in character_specs:
            char_identifier = spec.get("identifier", "UNKNOWN")
            char_type_text = "PRIMARY/MAIN character" if spec["type"] == "main" else f"SECONDARY character {char_identifier.split('_')[1]}"
            x_percent = spec["x_percent"]
            y_percent = spec["y_percent"]
            char_prompts.append(
                f"- [{char_identifier}] {char_type_text.upper()}: POSITION [X={x_percent}%, Y={y_percent}%]. POSE: {spec['pose']}."
            )

        final_prompt = f"IMAGE COMPOSITION INSTRUCTIONS:\n{chr(10).join(char_prompts)}\nMOVEMENT: {movement_instruction}"
        
        if locked_style:
            final_prompt += f"\nVISUAL STYLE: {locked_style}"

        try:
            model = genai.GenerativeModel('gemini-3-pro-image-preview')
            content = [final_prompt, bg_image]
            
            for spec in character_specs:
                char_image = Image.open(str(spec["image_path"]))
                if char_image.size[0] > 1024 or char_image.size[1] > 1024:
                    char_image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                content.append(char_image)
            
            response = model.generate_content(content)
            img_bytes = next((part.inline_data.data for part in response.parts if hasattr(part, 'inline_data')), None)
            
            if not img_bytes: return "", ""
            
            temp_filename = f"gen_{uuid.uuid4()}.png"
            temp_path = OUTPUT_DIR / temp_filename
            with open(temp_path, "wb") as f:
                f.write(img_bytes)
            
            self.previous_image_path = str(temp_path)
            final_path = str(temp_path)
            
            if has_placeholder and INSIGHTFACE_AVAILABLE:
                final_path = self.perform_identity_swap(temp_path, user_face_filename)
                self.previous_image_path = final_path
            
            return f"http://127.0.0.1:8000/static/generated/{Path(final_path).name}", final_path

        except Exception as e:
            print(f"❌ Image Generation Failed: {e}")
            return "", ""

    def compile_pdf(self, pages_data):
        from reportlab.lib.units import inch
        pdf_name = f"Story_{uuid.uuid4()}.pdf"
        pdf_path = OUTPUT_DIR / pdf_name
        page_width, page_height = 11 * inch, 8.5 * inch
        
        c = canvas.Canvas(str(pdf_path), pagesize=(page_width, page_height))
        
        for page in pages_data:
            image_path = page.get("image_path") if isinstance(page, dict) else None
            if image_path and os.path.exists(image_path):
                c.drawImage(image_path, 20, 100, width=page_width-40, height=page_height-140, preserveAspectRatio=True)
            
            c.setFont("Helvetica", 12)
            text = page.get("text", "")[:100] if isinstance(page, dict) else ""
            c.drawString(20, 30, f"Story: {text}")
            c.showPage()
        
        c.save()
        return f"http://127.0.0.1:8000/static/generated/{pdf_name}"

    def analyze_generated_style(self, image_path):
        return "Cinematic photorealistic style with dramatic lighting"
