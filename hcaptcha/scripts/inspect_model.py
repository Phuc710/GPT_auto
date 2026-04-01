import os
from ultralytics import YOLO

# Paths
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "hcaptcha.pt")
TEST_IMAGES = [
    os.path.join(os.path.dirname(__file__), "..", "test.png"),
    os.path.join(os.path.dirname(__file__), "..", "test2.png")
]

def inspect():
    if not os.path.exists(MODEL_PATH):
        print(f"[-] ERROR: Model not found at {MODEL_PATH}")
        return

    print(f"[*] Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)

    print("\n=== MODEL CLASS NAMES (Labels) ===")
    print(model.names)
    print("==================================\n")

    for img_path in TEST_IMAGES:
        if not os.path.exists(img_path):
            print(f"[-] Skipping {os.path.basename(img_path)} (Not found)")
            continue

        print(f"[*] Inspecting Image: {os.path.basename(img_path)}")
        
        # Run inference with very low confidence (0.1) to see everything
        results = model.predict(img_path, conf=0.1, verbose=False)
        
        if len(results[0].boxes) == 0:
            print("    [!] No objects detected even at 0.1 confidence.")
        else:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                name = model.names[cls_id]
                coords = box.xyxy[0].tolist()
                print(f"    - Detected: {name:15} | Confidence: {conf:.2f} | BBox: {[int(c) for c in coords]}")
        print("-" * 40)

if __name__ == "__main__":
    inspect()
