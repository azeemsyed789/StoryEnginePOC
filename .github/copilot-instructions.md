# Story Engine POC - AI Coding Agent Instructions

## Architecture Overview

This is a **full-stack AI image generation system** for creating visual stories with character identity injection:

```
Frontend (React + Vite)          Backend (FastAPI)              AI Services
├─ App.jsx (page builder)   →   ├─ main.py (FastAPI server) →  ├─ Google Gemini (image generation)
│  • Drag-drop canvas       │    ├─ engine_logic.py           │  ├─ InsightFace (face swap)
│  • 5-page story template  │    │  • StoryEngine class       │  └─ ReportLab (PDF compilation)
│  • Pose/character mgmt    │    │  • Page image generation    │
└─ Static file serving     └─   └─ Asset upload & PDF build  └─

Data Flow:
1. Admin builds story: Select backgrounds → Add characters → Define poses
2. User uploads face & clicks "Generate PDF"
3. Backend: For each page → Generate image with Gemini → Inject user face → Compile PDF
```

## Critical Patterns & Conventions

### 1. **Coordinate System & Positioning** (Engine-specific)
- **Frontend canvas**: 800×600px pixel coordinates (`x`, `y`)
- **Backend normalized**: 0-1 scale (divide by canvas size: `x/800`, `y/600`)
- **Gemini prompt**: Percentage positions ("left" = 0-33%, "center-left" = 33-50%)
- **Pose memory per page**: Each page tracks `primaryPose` and `secondaryPose` separately (see `INITIAL_PAGES` in App.jsx line 23)

### 2. **Data Models** (Pydantic - main.py)
```python
Element:          # Canvas item (character/asset)
  type: str       # "placeholder" (user) or "secondary" (other character)
  asset_filename: str  # Uploaded file reference
  pose: str       # Action text sent to Gemini ("Standing Naturally", etc.)
  x, y: float     # Normalized 0-1 position
  scale: float    # (Optional) sizing parameter

PageConfig:       # One page of the story
  background_filename: str  # Required—must exist in uploads
  text: str       # Story narrative
  primary_pose, secondary_pose: str  # Character actions (page-scoped)
  elements: List[Element]  # All positioned items on this page
```

### 3. **Gemini Prompt Architecture** (engine_logic.py, lines 190-260)
The image generation success depends on strict prompt structure:
- **Position anchors**: "far left (25% from left edge)" + "upper portion (20% from top)"
- **Character reference**: Background image + character crops added AFTER background for priority
- **Continuity**: Previous page image appended to prompt for visual consistency
- **Movement sync**: Both characters get synchronized action descriptions (see `movement_descriptions` dict, lines 210-225)
- **Critical rule**: Prompt explicitly states "Do NOT move or reposition characters" to prevent model hallucination

### 4. **File Organization**
```
static/
  uploads/        # User-uploaded backgrounds, faces, secondary characters (temp)
  generated/      # gen_*.png (intermediate images) + Story_*.pdf (final output)
```
**Important**: Filenames are UUIDs for uniqueness; no filename collision handling needed.

### 5. **Pose System**
- **Quick-select dropdowns**: Defined in App.jsx (lines 280-286 for primary, 310-316 for secondary)
- **Custom poses**: Users can type any action; it's passed directly to Gemini ("Flying / Hovering", "Holding a Weapon", etc.)
- **Synchronization**: When pose changes, all items of that type update immediately via `updatePoseAndItems` (lines 115-135)
- **Page persistence**: Poses are per-page, allowing different movements across 5 pages

## Development Workflows

### **Backend (Python/FastAPI)**
```bash
# Install dependencies
pip install -r requirements.txt

# Ensure .env file has GOOGLE_API_KEY=sk-...
# Ensure inswapper_128.onnx exists (face swap model, 128MB)

# Run server (auto-restart on changes)
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### **Frontend (React/Vite)**
```bash
cd frontend
npm install
npm run dev     # Vite dev server (port 5173, proxies to localhost:8000)
npm run build   # Production bundle
```

### **Testing Key Workflows**
1. **Upload flow**: POST `/upload-asset` → Returns `{url, filename}` for use in PageConfig
2. **Page generation**: POST `/generate-story` with payload structure (see data models)
3. **Face detection**: If `INSIGHTFACE_AVAILABLE=False`, face swap skipped (graceful fallback)
4. **PDF output**: ReportLab canvas with 16:9 aspect ratio maintained (11×8.5" landscape)

## Key Integration Points

### Gemini 3 Pro Image Model
- **Endpoint**: `genai.GenerativeModel('gemini-3-pro-image-preview')`
- **Input**: Multimodal (text + images)
- **Success metric**: Characters positioned correctly, background preserved, poses visible
- **Common failure**: Model recenters characters or ignores position prompts → increase positioning specificity

### InsightFace (Face Swap)
- **Model**: `inswapper_128.onnx` (must exist in repo root)
- **Flow**: Generate image with Gemini → Extract largest face from target (generated) and source (user) → Swap
- **Graceful degradation**: If disabled, skips face swap; returns Gemini output as-is
- **Return path**: Swapped image saved to `generated/` with new UUID filename

### Drag-Drop System (@dnd-kit)
- **Sensor**: PointerSensor with 5px activation distance (prevents accidental drag on click)
- **Z-index**: Placeholder (primary) = 100, secondary = 10
- **Coordinate sync**: Frontend x/y → normalized in payload → Gemini gets percentage positions

## Common Patterns

### **Page State Update** (functional in App.jsx)
```javascript
const updateActivePage = (updates) => {
  setPages(prev => {
    const copy = [...prev];
    copy[activePageIdx] = { ...copy[activePageIdx], ...updates };
    return copy;
  });
};
```
Used for: background selection, text editing, items list updates.

### **Async Upload Handler** (lines 146-157)
```javascript
// 1. FormData append file
// 2. POST to /upload-asset
// 3. Get {url, filename} in response
// 4. Store asset object (id, url, filename, name)
```
All uploads are temporary; only PageConfig `filename` is saved server-side.

### **Payload Normalization** (lines 176-194)
Frontend pixel coords → Divide by 800/600 → Backend sends to Gemini. This ensures positioning consistency across devices.

## Project-Specific Gotchas

1. **CORS middleware enabled**: All origins allowed (`allow_origins=["*"]`) for dev; restrict in production.
2. **Single user face per story**: `userFace` state is global; all pages use same user identity.
3. **Background required**: `generate_page_image` returns `"", ""` if background is null; invalid pages are filtered client-side.
4. **Pose must exist per character type**: If a page has a secondary character but no `secondaryPose` set, it defaults to "Standing Naturally".
5. **PDF aspect ratio**: Always 16:9; images scaled to fit landscape page while maintaining ratio.

## File Reference Guide

| File | Purpose | Key Functions/Components |
|------|---------|-------------------------|
| `main.py` | FastAPI server, routes | `/upload-asset`, `/generate-story` |
| `engine_logic.py` | Image generation pipeline | `StoryEngine.generate_page_image()`, `perform_identity_swap()`, `compile_pdf()` |
| `App.jsx` | React UI, page builder | Drag-drop canvas, asset management, form submission |
| `frontend/index.html` | Vite entry point | Single mount point for React |
| `requirements.txt` | Python dependencies | Gemini API, InsightFace, FastAPI, ReportLab |
| `frontend/package.json` | NPM dependencies | React, Vite, Tailwind, dnd-kit |

