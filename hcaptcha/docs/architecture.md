# HCaptcha Solver: Standard Flow Architecture

This document details the professional flow for bypassing modern HCaptcha challenges using Computer Vision and Relational AI.

## 🧬 Challenge Categories

We handle two distinct architectural patterns:

### 1. The Grid (Variant A)
- **Visuals**: A 3x3 or 4x4 matrix of individual images.
- **Goal**: Select all tiles matching the prompt (e.g., "bus").
- **Logic**:
    1.  **Image Splitting**: If the extension captures a single grid image, the Backend **Auto-Cropper** splits it into 9 slices.
    2.  **Recognition**: YOLOv8 predicts the class for each slice.
    3.  **Mapping**: If `confidence > threshold` and `class == prompt`, the slice index is returned.
- **Output**: `click_indices: [0, 2, 5]`

### 2. The Collage/Floating (Variant B)
- **Visuals**: A single large background image with floating cutout objects (Tàu hỏa, Xe tải...).
- **Goal**: Click specific objects (e.g., "vehicle on tracks").
- **Logic**:
    1.  **Full Image Inference**: YOLOv8 detects all objects in the single large image.
    2.  **Prompt Parsing**: Custom "Knowledge Base" maps the prompt (e.g., "tracks") to a category (e.g., `train`).
    3.  **Coordinate Extraction**: The center coordinates `{x, y}` of the detected bounding box are returned.
- **Output**: `click_coords: [{x: 100, y: 150}, ...]`

---

## 🧠 Relational AI Logic (Contextual)

For challenges like **"Select the animal taller than the cat"**:
1.  **Capture Reference**: Locate and extract the "Example" image (Cat).
2.  **Classify Reference**: Detect its class -> `Cat` (Height: 3).
3.  **Compare**: Detect animals in the grid/collage -> `Hippo` (Height: 8).
4.  **Match**: Hippo (8) > Cat (3) -> **CLICK!**

---

## 🖱 Anti-Bot Mouse Movement (Extension Level)

To ensure the bypass is successful, the extension implements:
- **Bézier Curves**: No straight lines. The cursor moves in arcs.
- **Delay Variation**: Clicks are not instantaneous. randomized millisecond delays simulate human reaction time.
- **Location Jitter**: Clicks are offset by ±3-5 pixels from the exact center.

---

## 📈 API Reference

| Endpoint | Method | Payload | Description |
| :--- | :--- | :--- | :--- |
| `/solve` | `POST` | `prompt`, `grid_images`, `type` | The main inference handler. Returns indices or coordinates. |
