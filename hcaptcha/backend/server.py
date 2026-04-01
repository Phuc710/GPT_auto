import os
import io
import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from ultralytics import YOLO

app = FastAPI(title="Advanced HCaptcha Solver API")

# Allow requests from the Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the YOLO model (Ensure hcaptcha.pt is in the parent folder)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "hcaptcha.pt")
try:
    if os.path.exists(MODEL_PATH):
        model = YOLO(MODEL_PATH)
        print(f"[INFO] Loaded model {MODEL_PATH}")
    else:
        model = YOLO("yolov8n.pt") 
        print(f"[WARNING] {MODEL_PATH} not found. using generic yolov8n.pt")
except Exception as e:
    model = None
    print(f"[ERROR] Failed to load model: {e}")

# --- KNOWLEDGE BASE (Relational & Contextual AI) ---
ANIMAL_TRAITS = {
    "mouse": {"height": 1, "diet": "omnivore"},
    "hamster": {"height": 1, "diet": "omnivore"},
    "hedgehog": {"height": 1, "diet": "omnivore"},
    "frog": {"height": 1, "diet": "insectivore"},
    "cat": {"height": 3, "diet": "carnivore"},
    "dog": {"height": 4, "diet": "omnivore"},
    "pig": {"height": 5, "diet": "omnivore"},
    "sheep": {"height": 5, "diet": "herbivore"},
    "cow": {"height": 7, "diet": "herbivore"},
    "horse": {"height": 8, "diet": "herbivore"},
    "hippo": {"height": 8, "diet": "herbivore"},
    "rhino": {"height": 8, "diet": "herbivore"},
    "elephant": {"height": 10, "diet": "herbivore"},
    "giraffe": {"height": 10, "diet": "herbivore"}
}

# Mapping prompt keywords to labels
LOGIC_MAPPING = {
    "tracks": ["train", "railway"],
    "water": ["boat", "fish", "rough sea", "airplane", "seaplane"],
    "air": ["airplane", "bird flying", "flying bat", "seaplane"],
    "sky": ["airplane", "bird flying", "flying bat", "seaplane", "sunflower"]
}

class SolveRequest(BaseModel):
    prompt: str
    grid_images: list[str]
    reference_image: str | None = None
    type: str = "grid"

def decode_image(base64_str):
    header = base64_str.split(",")[1] if "," in base64_str else base64_str
    return Image.open(io.BytesIO(base64.b64decode(header))).convert('RGB')

@app.post("/solve")
async def solve_captcha(req: SolveRequest):
    if not model:
        raise HTTPException(status_code=500, detail="Model not loaded")

    prompt = req.prompt.lower()
    print(f"\n[+] Processing Request - Prompt: '{prompt}', Type: {req.type}")

    # Set a VERY LOW confidence for HCaptcha images (they are often intentionally confusing)
    CONF_THRESHOLD = 0.05
    
    # === VARIANT A: 3x3 GRID ===
    if req.type == "grid":
        tiles = []
        if len(req.grid_images) == 1:
            full_img = decode_image(req.grid_images[0])
            w, h = full_img.size
            tw, th = w // 3, h // 3
            for r in range(3):
                for c in range(3):
                    box = (c * tw, r * th, (c + 1) * tw, (r + 1) * th)
                    tiles.append(full_img.crop(box))
        else:
            tiles = [decode_image(img_b64) for img_b64 in req.grid_images]

        click_indices = []
        
        for idx, tile in enumerate(tiles):
            results = model.predict(tile, verbose=False, conf=CONF_THRESHOLD)
            if len(results[0].boxes) > 0:
                # Find the top match for this tile
                best_box = results[0].boxes[0]
                cls_id = int(best_box.cls[0].item())
                detected_name = model.names[cls_id]
                conf = float(best_box.conf[0].item())
                
                print(f"    - Tile {idx}: Detected '{detected_name}' ({conf*100:.1f}%)")
                
                # Check 1: Direct name matching
                if any(word in prompt for word in [detected_name, detected_name.replace(" ", "")]):
                    click_indices.append(idx)
                    print(f"      -> MATCH (Direct Prompt)")
                
                # Check 2: Relational "taller than" (Default reference level: Cat=3)
                elif "taller than" in prompt:
                    detected_height = ANIMAL_TRAITS.get(detected_name, {}).get("height", 0)
                    if detected_height > 3: # Assuming cat height as baseline for tests
                        click_indices.append(idx)
                        print(f"      -> MATCH (Taller Than Cat)")

        return {"status": "success", "click_indices": click_indices}

    # === VARIANT B: COLLAGE / FREESTYLE (COORDINATES) ===
    elif req.type == "collage":
        full_img = decode_image(req.grid_images[0])
        results = model.predict(full_img, verbose=False, conf=CONF_THRESHOLD)
        
        click_coords = []
        
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            detected_name = model.names[cls_id]
            conf = float(box.conf[0].item())
            
            # Logic check for the prompt
            is_match = False
            
            # Direct match
            if any(word in prompt for word in [detected_name, detected_name.replace(" ", "")]):
                is_match = True
            
            # Key-logic match (e.g. tracks, water, sky)
            for key, labels in LOGIC_MAPPING.items():
                if key in prompt and detected_name in labels:
                    is_match = True
                    break

            if is_match:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                click_coords.append({"x": cx, "y": cy, "label": detected_name, "conf": conf})
                print(f"    - Found '{detected_name}' at ({cx}, {cy}) with {conf*100:.1f}% confidence. -> ADDING COORDINATES")

        return {"status": "success", "click_coords": click_coords}

    return {"status": "error", "message": "Unknown type"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
