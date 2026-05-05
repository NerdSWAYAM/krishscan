import os

_disease_model = None
_resnet_model = None

def get_disease_model():
    import torch
    import torch.nn as nn
    import timm
    from huggingface_hub import hf_hub_download
    global _disease_model
    if _disease_model is None:
        model_path = hf_hub_download(repo_id="VisionaryQuant/5_Crop_Disease_Detection", filename="best_crop_disease_model.pt")
        model = timm.create_model('efficientnet_b3', pretrained=False)
        model.classifier = nn.Sequential(
            nn.Linear(model.classifier.in_features, 17)
        )
        state_dict = torch.load(model_path, map_location=torch.device('cpu'))
        model.load_state_dict(state_dict)
        model.eval()
        _disease_model = model
    return _disease_model

def get_resnet_model():
    import os
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    import tensorflow as tf
    global _resnet_model
    if _resnet_model is None:
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'MLmodels', 'resnet50_transfer_best.h5')
        _resnet_model = tf.keras.models.load_model(model_path)
    return _resnet_model

CLASS_NAMES = [
    "Corn___Common_Rust", "Corn___Gray_Leaf_Spot", "Corn___Healthy", "Corn___Northern_Leaf_Blight",
    "Potato___Early_Blight", "Potato___Healthy", "Potato___Late_Blight",
    "Rice___Brown_Spot", "Rice___Healthy", "Rice___Leaf_Blast", "Rice___Neck_Blast",
    "Sugarcane___Bacterial_Blight", "Sugarcane___Healthy", "Sugarcane___Red_Rot",
    "Wheat___Brown_Rust", "Wheat___Healthy", "Wheat___Yellow_Rust"
]
