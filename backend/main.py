import os
import shutil
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from auth import authenticate_user, create_access_token, get_current_user
from models import User, UploadedAsset
from sqlalchemy.orm import Session
from engine_logic import StoryEngine
from database import SessionLocal, engine, Base


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
OUTPUT_DIR = BASE_DIR / "static" / "generated"

app = FastAPI(title="Identity Story Engine API")


@app.on_event("startup")
async def startup_event():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
engine = StoryEngine()


# --- DATA MODELS ---
class Element(BaseModel):
    type: str
    asset_filename: Optional[str] = None
    pose: str
    x: float
    y: float
    scale: Optional[float] = 1.0


class PageConfig(BaseModel):
    background_filename: str
    text: str
    primary_pose: Optional[str] = "Standing Naturally"
    secondary_pose: Optional[str] = "Standing Naturally"
    elements: List[Element]


class StoryRequest(BaseModel):
    user_face_filename: str
    pages: List[PageConfig]


# --- UPLOAD ENDPOINT ---
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}


@app.post("/upload-asset")
async def upload_asset(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_ext}")

    try:
        new_filename = f"{uuid.uuid4()}{file_ext}"
        save_path = UPLOAD_DIR / new_filename
        with open(save_path, "wb+") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "url": f"http://127.0.0.1:8000/static/uploads/{new_filename}",
            "filename": new_filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


# --- STORY GENERATION ENDPOINT ---
@app.post("/generate-story")
async def generate_story(
    request: StoryRequest, current_user: User = Depends(get_current_user)
):
    if current_user.role != "user":
        raise HTTPException(status_code=403, detail="Admins cannot generate stories")

    generated_pages = []
    generated_urls = []
    locked_style = None

    for i, page in enumerate(request.pages):
        print(f"Generating Page {i+1}...")
        image_url, image_path = engine.generate_page_image(
            page,
            request.user_face_filename,
            locked_style,
            primary_pose=page.primary_pose,
            secondary_pose=page.secondary_pose,
        )
        if i == 0 and image_path:
            locked_style = engine.analyze_generated_style(image_path)
        generated_pages.append({"image_path": image_path, "text": page.text})
        generated_urls.append(image_url)

    pdf_url = engine.compile_pdf(generated_pages)

    return {"status": "success", "pdf_url": pdf_url, "image_urls": generated_urls}


@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@app.post("/upload-face")
async def upload_face(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(lambda: SessionLocal()),
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    asset = UploadedAsset(filename=file.filename, user_id=current_user.id, type="face")
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # return {"filename": file.filename, "url": f"/static/uploads/{file.filename}"}
    return {
        "url": f"http://127.0.0.1:8000/static/uploads/{file.filename}",
        "filename": file.filename,
    }


@app.get("/user-faces")
def get_user_faces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(lambda: SessionLocal()),
):
    """
    Return face assets. Always provide absolute URLs so the frontend can render
    images regardless of which origin it is running on.
    """
    if current_user.role == "admin":
        faces = db.query(UploadedAsset).filter(UploadedAsset.type == "face").all()
    else:
        faces = (
            db.query(UploadedAsset)
            .filter(
                UploadedAsset.type == "face", UploadedAsset.user_id == current_user.id
            )
            .all()
        )

    base_static_url = "http://127.0.0.1:8000/static/uploads"
    return [
        {"filename": f.filename, "url": f"{base_static_url}/{f.filename}"}
        for f in faces
    ]
