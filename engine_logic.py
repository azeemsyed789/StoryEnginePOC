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

# --- IDENTITY ENGINE (INSIGHTFACE) ---
# --- IDENTITY ENGINE (LAZY LOADING SETUP) ---
print("--- IDENTITY ENGINE INITIALIZED (WAITING FOR CALL) ---")
INSIGHTFACE_AVAILABLE = True # We assume true, but will check during swap
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
        global face_app, swapper  # <--- CRITICAL: Allows the function to update the global variables
        
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

        # Get background image
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

        # Load background image
        bg_image = Image.open(str(bg_path))
        
        # Build character descriptions with exact grid positions
        character_specs = []
        has_placeholder = False
        secondary_char_count = 0
        
        for el in getattr(page_config, "elements", []):
            x_val = getattr(el, "x", 0.5)
            y_val = getattr(el, "y", 0.5)
            pose = getattr(el, "pose", "standing")
            char_type = getattr(el, "type", "")
            
            # Convert to percentage positions (0-100)
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

        # Get page number from context (estimate based on previous_image_path history)
        # This is a simple heuristic - page 1 if no previous, page 2+ if previous exists
        page_num = 1
        if self.previous_image_path:
            # Count generated images to estimate page number
            gen_files = list(OUTPUT_DIR.glob("gen_*.png"))
            page_num = min(len(gen_files) + 1, 5)  # Cap at 5
        
        # Use custom poses if provided, otherwise use page-based defaults
        if primary_pose and secondary_pose:
            # Custom poses provided by user
            movement_instruction = f"PRIMARY CHARACTER: {primary_pose}. SECONDARY CHARACTER: {secondary_pose}. Both characters should perform these exact movements together in synchronized action."
        else:
            # Fallback to page-based movement descriptions
            movement_descriptions = {
                1: "BOTH CHARACTERS DANCING: Both primary and secondary characters are dancing together with energetic, lively dance moves. Synchronized dancing poses with motion and energy.",
                2: "BOTH CHARACTERS FIGHTING: Both primary and secondary characters in combat/fighting stances. Dynamic fighting movements, action-packed positions, both engaged in battle.",
                3: "BOTH CHARACTERS WALKING: Both primary and secondary characters walking together. Casual walking poses, natural movement, both moving in the same direction.",
                4: "BOTH CHARACTERS RUNNING TOWARDS EACH OTHER: Both primary and secondary characters running towards each other with dynamic movement. High-energy rushing motion, intense action poses.",
                5: "BOTH CHARACTERS IN EPIC CONFRONTATION: Both primary and secondary characters in an epic, powerful confrontation pose. Climactic stance, dramatic powerful movements, both in intense action."
            }
            movement_instruction = movement_descriptions.get(page_num, "Add dynamic synchronized movement to both characters.")

        # Build the prompt - use EXTREMELY precise positioning language
        char_prompts = []
        for spec in character_specs:
            char_identifier = spec.get("identifier", "UNKNOWN")
            char_type_text = "PRIMARY/MAIN character" if spec["type"] == "main" else f"SECONDARY character {char_identifier.split('_')[1]}"
            
            # Use EXACT percentages with grid-based positioning (10% increments for precision)
            x_percent = spec["x_percent"]
            y_percent = spec["y_percent"]
            
            # Create a coordinate grid description for maximum precision
            x_grid = (x_percent // 10) * 10  # Round to nearest 10%
            y_grid = (y_percent // 10) * 10
            
            x_desc = f"EXACTLY {x_percent}% from left edge (grid position {x_grid}%)"
            y_desc = f"EXACTLY {y_percent}% from top edge (grid position {y_grid}%)"
            
            char_prompts.append(
                f"- [{char_identifier}] {char_type_text.upper()}: POSITION [X={x_percent}%, Y={y_percent}%]. MUST appear at EXACTLY {x_desc}, {y_desc}. POSE: {spec['pose']}. CRITICAL RULE: Character position MUST be precise. Do NOT adjust. Do NOT move. Match reference position exactly."
            )

        final_prompt = f"""IMAGE COMPOSITION INSTRUCTIONS - FOLLOW THESE RULES EXACTLY AND STRICTLY:

**BACKGROUND (IMMUTABLE - NON-NEGOTIABLE):**
The background image provided is FINAL and CANNOT be modified in any way.
- Keep background 100% unchanged
- NO style changes
- NO color adjustments
- NO blending or fading
- Use background EXACTLY as provided
- Background is locked and immutable

**CHARACTER POSITIONS (STRICT GRID-BASED COORDINATES):**
Each character has an EXACT position that MUST be preserved:
{chr(10).join(char_prompts)}

**MOVEMENT INSTRUCTIONS:**
{movement_instruction}

**MANDATORY RULES (MUST FOLLOW ALL):**
1. Background CANNOT be modified - use exactly as provided
2. Each character MUST be at its specified grid position
3. X coordinate: {" ".join([f"[{spec.get('identifier', 'UNKNOWN')}]={spec['x_percent']}%" for spec in character_specs])}
4. Y coordinate: {" ".join([f"[{spec.get('identifier', 'UNKNOWN')}]={spec['y_percent']}%" for spec in character_specs])}
5. Do NOT move characters away from specified positions
6. Do NOT adjust positions for aesthetic reasons
7. Do NOT center characters unless position specifies center
8. Do NOT modify background colors, lighting, or style
9. Maintain 16:9 aspect ratio
10. Photorealistic cinematic style with precise character placement

**REFERENCE IMAGES PROVIDED:**
- First image: Background (use exactly)
- Following images: Character reference crops (position at specified coordinates)

Output image must have: unchanged background + characters at exact positions.
"""
        
        if locked_style:
            final_prompt += f"\nVISUAL STYLE: {locked_style}"

        print(f"📝 Prompt: {final_prompt[:250]}...")

        # --- Image Generation with STRICT Background Preservation and Positioning ---
        try:
            model = genai.GenerativeModel('gemini-3-pro-image-preview')
            
            # Build content: prompt + background as PRIMARY reference (first image for lock)
            # Background MUST be first to establish immutable reference
            content = [final_prompt, bg_image]
            
            # Add character reference images AFTER background
            # Each character image includes its identifier in memory for Gemini reference
            for spec in character_specs:
                try:
                    char_image = Image.open(str(spec["image_path"]))
                    # Preserve original size for accuracy - don't resize to avoid distortion
                    # Only resize if absolutely necessary (max 1024 for API)
                    if char_image.size[0] > 1024 or char_image.size[1] > 1024:
                        char_image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                    
                    content.append(char_image)
                    print(f"✅ Added character [{spec.get('identifier', 'UNKNOWN')}] at position [{spec['x_percent']}%, {spec['y_percent']}%]")
                except Exception as e:
                    print(f"⚠️ Error loading character image: {e}")
            
            # Include previous image for continuity (but don't let it affect current page background)
            if self.previous_image_path and os.path.exists(self.previous_image_path):
                try:
                    prev_image = Image.open(self.previous_image_path)
                    if prev_image.size[0] > 512 or prev_image.size[1] > 512:
                        prev_image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                    content.append(prev_image)
                except Exception as e:
                    print(f"⚠️ Error loading previous image: {e}")
            
            print(f"📡 Sending to Gemini: background + {len(character_specs)} character images")
            response = model.generate_content(content)
            
            if not response:
                print(f"❌ No response from Google API")
                return "", ""
            
            # Extract image from response
            img_bytes = None
            if response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data'):
                        img_bytes = part.inline_data.data
                        break
            
            if not img_bytes:
                print(f"❌ No image data in response")
                return "", ""
            
            # Save generated image
            temp_filename = f"gen_{uuid.uuid4()}.png"
            temp_path = OUTPUT_DIR / temp_filename
            with open(temp_path, "wb") as f:
                f.write(img_bytes)
            
            print(f"✅ Image generated successfully")
            
            # Update reference for next image
            self.previous_image_path = str(temp_path)
            
            final_path = str(temp_path)
            if has_placeholder and INSIGHTFACE_AVAILABLE:
                print("🔄 Injecting User Identity...")
                final_path = self.perform_identity_swap(temp_path, user_face_filename)
                self.previous_image_path = final_path
            
            return f"http://127.0.0.1:8000/static/generated/{Path(final_path).name}", final_path

        except Exception as e:
            print(f"❌ Image Generation Failed: {e}")
            import traceback
            traceback.print_exc()
            return "", ""

    def compile_pdf(self, pages_data):
        from reportlab.lib.units import inch
        pdf_name = f"Story_{uuid.uuid4()}.pdf"
        pdf_path = OUTPUT_DIR / pdf_name

        # Use landscape orientation for 16:9 ratio images
        page_width = 11 * inch  # Landscape width
        page_height = 8.5 * inch  # Landscape height
        
        c = canvas.Canvas(str(pdf_path), pagesize=(page_width, page_height))
        
        for page in pages_data:
            image_path = page.get("image_path") if isinstance(page, dict) else None
            if image_path and os.path.exists(image_path):
                # Load image to get dimensions and calculate 16:9 fit
                try:
                    img = Image.open(image_path)
                    img_width, img_height = img.size
                    aspect_ratio = img_width / img_height
                    
                    # Target 16:9 aspect ratio
                    target_aspect = 16 / 9
                    
                    # Calculate dimensions to fit page while maintaining 16:9
                    max_width = page_width - 40  # 20pt margin each side
                    max_height = page_height - 100  # Top and bottom for text
                    
                    if max_width / max_height > target_aspect:
                        # Height is limiting factor
                        draw_height = max_height
                        draw_width = draw_height * target_aspect
                    else:
                        # Width is limiting factor
                        draw_width = max_width
                        draw_height = draw_width / target_aspect
                    
                    # Center horizontally
                    x_pos = (page_width - draw_width) / 2
                    y_pos = page_height - 40 - draw_height
                    
                    c.drawImage(image_path, x_pos, y_pos, width=draw_width, height=draw_height, preserveAspectRatio=True)
                except Exception as e:
                    print(f"⚠️ Error processing image for PDF: {e}")
            
            # Add text below image
            c.setFont("Helvetica", 12)
            text = page.get("text", "")[:100] if isinstance(page, dict) else ""
            c.drawString(20, 30, f"Story: {text}")
            c.showPage()
        
        c.save()
        return f"http://127.0.0.1:8000/static/generated/{pdf_name}"

    def analyze_generated_style(self, image_path):
        return "Cinematic photorealistic style with dramatic lighting"
