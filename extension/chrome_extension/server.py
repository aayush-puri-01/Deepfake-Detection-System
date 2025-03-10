import os
import base64
import io
import traceback

import torch
import torch.nn as nn
import torch.optim as optim

from torch.utils.data import DataLoader
import torch.nn.functional as F
from torchvision import datasets, transforms
from torch.utils.data import random_split
from torch.autograd import Variable
from PIL import Image
import numpy as np
import torchvision
import random
from transformers import CLIPProcessor, CLIPModel
from clipped_freqnet import freqnet

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/analyze": {"origins": "chrome-extension://*"}})  # Enable CORS for all routes to allow requests from your Chrome extension

#whitelisting approach, restrict CORS to chrome extensions only

device = torch.device("cpu")

class HybridDeepfakeDetector(nn.Module):
    def __init__(self, freq_model, clip_model_name="openai/clip-vit-large-patch14", device="cuda"):
        super(HybridDeepfakeDetector, self).__init__()
        self.device = device

        # Load FreqNet
        self.freqnet = freq_model.to(self.device)

        # Load CLIP Model
        self.clip_model = CLIPModel.from_pretrained(clip_model_name).to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained(clip_model_name)

        # Define Fully Connected Classifier
        self.fc = nn.Linear(512 + 768, 1)  # FreqNet (512) + CLIP (768)

        # ImageNet Denormalization
        imagenet_mean = [0.485, 0.456, 0.406]
        imagenet_std = [0.229, 0.224, 0.225]
        self.denormalize = transforms.Compose([
            transforms.Normalize(mean=[-m / s for m, s in zip(imagenet_mean, imagenet_std)],
                                 std=[1 / s for s in imagenet_std]),
            # transforms.Lambda(lambda x: x.clamp(0, 1))  # Clamp to [0,1]
            transforms.Lambda(HybridDeepfakeDetector.clamp_image)
        ])

    @staticmethod
    def clamp_image(tensor):
        return tensor.clamp(0, 1)
    
    def extract_clip_features(self, images):
        """
        Extract CLIP embeddings from images.
        """
        inputs = self.clip_processor(images=images, return_tensors="pt", padding=True)
        #inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            embeddings = self.clip_model.get_image_features(**inputs)
        # return embeddings.to(self.device)
        return embeddings

    def forward(self, freq_input, clip_input):
        """
        freq_input: Image tensors normalized with ImageNet stats for FreqNet
        clip_input: Same image tensors (but denormalized) for CLIP
        """
        # Get frequency-based features from FreqNet
        freq_features = self.freqnet(freq_input)

        # Get semantic embeddings from CLIP
        denormalized_images = torch.stack([self.denormalize(image) for image in clip_input])
        clip_features = self.extract_clip_features(denormalized_images)

        # Normalize features and concatenate
        freq_features = F.normalize(freq_features, dim=-1)
        clip_features = F.normalize(clip_features, dim=-1)
        combined_features = torch.cat((freq_features, clip_features), dim=-1)

        # Classifier output
        logits = self.fc(combined_features)
        return logits.squeeze()
    

freqnet_model = freqnet(num_classes=2) 
model = HybridDeepfakeDetector(freqnet_model, device=device).to(device)

path_to_checkpoint = "./checkpoint_bisheyepoch_8.pth"
checkpoint = torch.load(path_to_checkpoint, map_location = device, weights_only=False)
#model = checkpoint['model'].to(device)
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]) 
])

def preprocess_image(image_data, device = "cpu"):
    # Convert base64 data to PIL Image
    image_data = image_data.split(',')[1]  # Remove the "data:image/png;base64," part
    image_bytes = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")
    
    # Preprocess the image
    image_tensor = transform(image)
    return image_tensor.unsqueeze(0).to(device) #Add batch dimension

@app.route('/analyze', methods = ['POST'])
def analyze_image():
    try:
        #get image data from request
        data = request.json
        image_data = data.get('image')

        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400
        
        #preprocess and tensorize the image
        input_tensor = preprocess_image(image_data)

        #run inference
        with torch.no_grad():
            input_tensor_cloned = input_tensor.clone()
            logit = model(input_tensor, input_tensor_cloned)
            probability = torch.sigmoid(logit).item()

            is_deepfake = probability <= 0.5

        return jsonify({
            'isDeepfake': bool(is_deepfake),
            'confidence': round(100 - probability*100, 2) if is_deepfake else round(probability*100, 2)
        })
    
    except ValueError as ve:
        # Log error and provide more details
        app.logger.error("ValueError: %s", str(ve))
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        # Log full error stack trace
        app.logger.error("Exception: %s", traceback.format_exc())
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='127.0.0.1', port = 5000, debug=True)