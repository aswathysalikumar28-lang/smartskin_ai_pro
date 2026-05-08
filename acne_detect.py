"""
acne_detect.py — Acne Severity Detection using PyTorch Deep Learning Model
"""

import cv2
import numpy as np
import torch
import torch.nn as nn

IMG_SIZE = 64

# ── CNN Model (same architecture as training) ──
class AcneCNN(nn.Module):
    def __init__(self):
        super(AcneCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(), nn.BatchNorm2d(32), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.BatchNorm2d(64), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(), nn.BatchNorm2d(128), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 8 * 8, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 3)
        )

    def forward(self, x):
        return self.classifier(self.features(x))


label_map = {0: "Mild", 1: "Moderate", 2: "Severe"}

advice_map = {
    "Mild": {
        "description": "You have mild acne — a few small pimples or blackheads. This is very common and manageable!",
        "tips": [
            "Wash your face twice daily with a gentle cleanser",
            "Use a salicylic acid cleanser to unclog pores",
            "Apply aloe vera gel or tea tree oil on spots",
            "Avoid touching your face",
            "Stay hydrated and eat less oily food"
        ],
        "products": ["Salicylic Acid Cleanser", "Aloe Vera Gel", "Light Moisturizer", "SPF 30 Sunscreen"],
        "see_doctor": False,
        "color": "#f5a623"
    },
    "Moderate": {
        "description": "You have moderate acne — multiple inflamed pimples and possible redness. Consistent care is needed.",
        "tips": [
            "Use a niacinamide serum daily to reduce inflammation",
            "Apply benzoyl peroxide spot treatment at night",
            "Never pop or squeeze pimples",
            "Change pillowcases every 2-3 days",
            "Consider reducing dairy and sugar intake",
            "Track pimples in the Skin Pattern Tracker"
        ],
        "products": ["Niacinamide Serum", "Benzoyl Peroxide Cream", "Oil-free Moisturizer", "Matte Sunscreen"],
        "see_doctor": False,
        "color": "#e05c1a"
    },
    "Severe": {
        "description": "You have severe acne — deep cysts, widespread inflammation, or scarring. Professional help is recommended.",
        "tips": [
            "See a dermatologist as soon as possible",
            "Avoid harsh scrubs or over-washing",
            "Use gentle fragrance-free products only",
            "Do not pop or pick at cysts — this causes scarring",
            "Stay consistent with any prescribed treatment",
            "Manage stress through yoga or meditation"
        ],
        "products": ["Gentle Cleanser", "Prescribed Topical Treatment", "Fragrance-free Moisturizer"],
        "see_doctor": True,
        "color": "#c0392b"
    }
}

# Load model once
_model = None

def load_model():
    global _model
    if _model is None:
        _model = AcneCNN()
        _model.load_state_dict(torch.load("acne_model.pth", map_location=torch.device("cpu")))
        _model.eval()
    return _model

def detect_acne_severity(image_path):
    try:
        model = load_model()

        img = cv2.imread(image_path)
        if img is None:
            return {"error": "Could not read image"}

        img_resized = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        img_normalized = img_resized.transpose(2, 0, 1) / 255.0
        img_tensor = torch.tensor(img_normalized, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            output = model(img_tensor)
            probabilities = torch.softmax(output, dim=1)[0]
            class_idx = torch.argmax(probabilities).item()
            confidence = float(probabilities[class_idx]) * 100

        severity = label_map[class_idx]
        result = advice_map[severity].copy()
        result["severity"] = severity
        result["confidence"] = round(confidence, 1)
        return result

    except Exception as e:
        return {"error": str(e)}
