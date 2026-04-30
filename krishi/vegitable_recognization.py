from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import torch

model_name = "dima806/vegetable_15_types_image_detection"

# Load model
processor = AutoImageProcessor.from_pretrained(model_name)
model = AutoModelForImageClassification.from_pretrained(model_name)

model.eval()

# Load image
image = Image.open("tomoto (2).jpg").convert("RGB")

# Preprocess
inputs = processor(images=image, return_tensors="pt")

# Inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits

# Prediction
predicted_class_id = logits.argmax(-1).item()
label = model.config.id2label[predicted_class_id]
probs = torch.nn.functional.softmax(logits, dim=-1)
confidence = probs[0][predicted_class_id].item()

print(f"Prediction: {label}")
print(f"Confidence: {confidence:.4f}")

print(model.config.id2label)