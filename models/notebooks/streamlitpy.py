import os
import cv2
import mediapipe as mp
import torch
from torchvision import datasets, transforms
import numpy as np
import torchvision
import random
import streamlit as st
from freqnet_cpu import freqnet
import matplotlib.pyplot as plt
from PIL import Image

transform = transforms.Compose([
    transforms.Resize((224, 224)),  # Assuming the model accepts 224x224 images
    transforms.ToTensor(),  # Convert the image to a PyTorch tensor
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # Standard ImageNet normalization
])

model = freqnet(num_classes = 2)

@st.cache_resource
def loadandcache_model(device):
    checkpt_path = "./freqnet_epoch_9.pth"
    cpoint = torch.load(checkpt_path, map_location=device)
    #cpoint.keys()
    model.load_state_dict(cpoint)
    #model.load_state_dict(cpoint['model_state_dict'])
    model.eval()
    return model

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

def make_frames(video_path, frame_sample_rate=10, box_scaling=2):
  vid = cv2.VideoCapture(video_path)
  #opencv , imread, VideoCapture, the image frames are loaded in the BGR color space

  total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
  frame_indices = np.linspace(0, total_frames-1, frame_sample_rate, dtype=int)

  face_frames = []

  for frame_index in frame_indices:
    vid.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = vid.read()

    if not ret:
      continue

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    #Detect the face from the frames using the mediapipe function

    faces = face_detection.process(rgb_frame)

    if faces.detections:
      for detection in faces.detections:
        bounding_box = detection.location_data.relative_bounding_box
        im_height, im_width, im_channel = frame.shape

        x, y, w, h = (int(bounding_box.xmin * im_width),
                      int(bounding_box.ymin * im_height),
                      int(bounding_box.width * im_width),
                      int(bounding_box.height * im_height))

        cx, cy = x + w // 2, y + h // 2  # Center of the box
        w, h = w * box_scaling, h * box_scaling  # Scale width and height
        x, y = cx - w / 2, cy - h / 2  # Adjust coordinates

        #ensuring that the box stays within the frame
        x, y = max(0, int(x)), max(0, int(y))
        w, h = min(int(w), im_width - x), min(int(h), im_height - y)

        face = rgb_frame[y:y+h, x:x+w]
        face_frames.append(face)

  vid.release()
  return face_frames

def visualize_face_frames(face_frames, num_rows=2, num_columns=5):
    num_frames = len(face_frames)
    
    # Correct way to create figure and axes
    fig, axes = plt.subplots(num_rows, num_columns, figsize=(15, 5))
    
    # Flatten axes if it's a 2D array
    axes = axes.flatten() if num_rows > 1 else axes
    
    for i in range(min(num_frames, num_rows * num_columns)):
        axes[i].imshow(face_frames[i])
        axes[i].axis('off')
        axes[i].set_title(f"Face : {i+1}")
    
    # Hide any unused subplots
    for j in range(min(num_frames, num_rows * num_columns), num_rows * num_columns):
        fig.delaxes(axes[j])
    
    plt.tight_layout()
    st.pyplot(fig)  # Pass the figure to st.pyplot()
    plt.close(fig)  



def classify_frames(face_frames, DLmodel, transformation_definition=transform):
  if not face_frames:
    return "Not able to detect any faces"

  logits = []

  for face in face_frames:
    face = Image.fromarray(face)
    face_tensor = transformation_definition(face).unsqueeze(0)

    with torch.no_grad():
      logit = DLmodel(face_tensor)
      logits.append(logit)

  probabilities = [torch.sigmoid(logit) for logit in logits]
  print(probabilities)

  real_count, fake_count = 0, 0
  for prob in probabilities:
    if prob > 0.5:
      real_count += 1
    else:
      fake_count += 1

  print(f"Real Count: {real_count}\nFake Count: {fake_count}")

  if real_count != fake_count:
    if real_count >= 3:
      return "This appears to be a Real Video! Yayy!"
    else:
      return "Oh no! This is a deepfake! Call Policia!"
  else:
    average_probability = torch.stack(probabilities).mean().item()
    print(average_probability)
    if average_probability > 0.549:
        return "This appears to be a Real Video! Yayy!"
    else:
        return "Oh no! This is a deepfake! Call Policia!"
    
st.title("Deepfake Detection System")

uploaded_file = st.file_uploader("Upload Video File", type=["mp4", "avi", "mov"])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = loadandcache_model(device)

if uploaded_file is not None:
    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.read())
    
    st.video(uploaded_file)
    st.write("Processing video...")

    face_frames = make_frames("temp_video.mp4")
    result = classify_frames(face_frames, model)
    st.success(f"The video is classified as: {result}")

    if face_frames:
        st.write("Extracted Face Frames:")
        visualize_face_frames(face_frames)

