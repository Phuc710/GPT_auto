# YOLOv8 Training Boilerplate for HCaptcha - 2026 Edition

## 1. Environment Setup
Run these commands in a Colab Cell:

```python
!pip install ultralytics
from ultralytics import YOLO
import os
from google.colab import drive

# Mount Google Drive
drive.mount('/content/drive')

# Set Project Path (Update this to your hcapcha folder in Drive)
PROJECT_DIR = "/content/drive/My Drive/hcapcha"
os.chdir(PROJECT_DIR)
```

## 2. Configuration (`hcaptcha_config.yaml`)
Ensure your `hcaptcha_config.yaml` is in the `PROJECT_DIR`.
It should look like this:
```yaml
path: /content/drive/My Drive/hcapcha/dataset/raw
train: images/train
val: images/val
nc: 11
names: ['bus', 'bicycle', 'motorcycle', 'airplane', 'boat', 'train', 'truck', 'cow', 'sheep', 'lion', 'shark']
```

## 3. Training
Start the training process with YOLOv10/v8 (Nano for speed):

```python
# Load pre-trained nano model
model = YOLO('yolov8n.pt') 

# Train
model.train(
    data='hcaptcha_config.yaml', 
    epochs=100, 
    imgsz=128, 
    batch=32, 
    device=0, 
    project='hcaptcha_runs', 
    name='hcaptcha_v1'
)
```

## 4. Evaluation & Export
Once trained, export the model for your Backend API:

```python
# Export to ONNX (Standard for cross-platform API)
model = YOLO('hcaptcha_runs/hcaptcha_v1/weights/best.pt')
model.export(format='onnx')

# Test Inference
results = model.predict(source='dataset/raw/bus/example.jpg', conf=0.5)
results[0].show()
```
