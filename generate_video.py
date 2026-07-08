#!/usr/bin/env python3
"""
CaptionChameleon - 10 Second Video Presentation Generator
Creates a professional intro video showcasing the project
"""

import cv2
import numpy as np
from pathlib import Path
import time

def create_text_frame(text, size, color=(255, 255, 255), bg_color=(15, 23, 42)):
    """Create a frame with centered text"""
    frame = np.full((1080, 1920, 3), bg_color, dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Main text
    font_scale = size
    thickness = 3
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    x = (1920 - text_size[0]) // 2
    y = (1080 + text_size[1]) // 2
    
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    return frame

def create_gradient_frame(color1=(0, 102, 204), color2=(147, 51, 234)):
    """Create a gradient background frame"""
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    for i in range(1080):
        ratio = i / 1080
        b = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        r = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        frame[i, :] = [b, g, r]
    return frame

def add_text_overlay(frame, text, pos=(960, 540), color=(255, 255, 255), size=2):
    """Add text to an existing frame"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, size, 2)[0]
    x = pos[0] - text_size[0] // 2
    y = pos[1] + text_size[1] // 2
    cv2.putText(frame, text, (x, y), font, size, color, 2, cv2.LINE_AA)
    return frame

def create_style_boxes_frame():
    """Create frame with 4 style boxes"""
    frame = np.full((1080, 1920, 3), (243, 243, 243), dtype=np.uint8)
    
    # Title
    frame = add_text_overlay(frame, "Four Perfect Styles", (960, 100), (32, 33, 36), 3)
    
    # 4 boxes
    box_width = 400
    box_height = 350
    box_y = 350
    colors = [
        (0, 102, 204),      # Blue - Formal
        (147, 51, 234),     # Purple - Sarcastic
        (0, 255, 136),      # Green - Tech
        (255, 140, 0)       # Orange - Casual
    ]
    labels = ["FORMAL", "SARCASTIC", "TECH", "CASUAL"]
    
    start_x = 240
    for i, (color, label) in enumerate(zip(colors, labels)):
        x = start_x + i * 420
        cv2.rectangle(frame, (x, box_y), (x + box_width, box_y + box_height), color, -1)
        frame = add_text_overlay(frame, label, (x + box_width//2, box_y + box_height//2 + 50), 
                               (255, 255, 255), 2)
    
    return frame

def generate_video(output_path="CaptionChameleon_Intro.mp4", fps=30, duration=10):
    """Generate 10-second intro video"""
    
    width, height = 1920, 1080
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = fps * duration
    print(f"Generating {duration}s video at {fps}fps ({total_frames} frames)...\n")
    
    # Sequence of scenes
    scenes = []
    
    # Scene 1: Title (2 seconds)
    print("  Scene 1: Title slide (2s)")
    title_frame = create_gradient_frame((0, 102, 204), (147, 51, 234))
    title_frame = add_text_overlay(title_frame, "🦎 CaptionChameleon", (960, 400), 
                                   (255, 255, 255), 4)
    title_frame = add_text_overlay(title_frame, "Adaptive Multi-Style Video Captioning", (960, 700), 
                                   (0, 255, 136), 2.5)
    for _ in range(fps * 2):
        scenes.append(title_frame)
    
    # Scene 2: Four Styles (3 seconds)
    print("  Scene 2: Four styles (3s)")
    styles_frame = create_style_boxes_frame()
    for _ in range(fps * 3):
        scenes.append(styles_frame)
    
    # Scene 3: Key Features (3 seconds)
    print("  Scene 3: Key features (3s)")
    features_frame = np.full((1080, 1920, 3), (31, 31, 58), dtype=np.uint8)
    features = [
        "✓ Zero-Shot Learning",
        "✓ Batch API Calls",
        "✓ 10x Parallel Processing",
        "✓ Production Ready Docker"
    ]
    y_offset = 250
    for feature in features:
        features_frame = add_text_overlay(features_frame, feature, (960, y_offset), 
                                         (0, 255, 136), 1.8)
        y_offset += 150
    for _ in range(fps * 3):
        scenes.append(features_frame)
    
    # Scene 4: Call to Action (2 seconds)
    print("  Scene 4: Call to action (2s)")
    cta_frame = create_gradient_frame((0, 255, 136), (0, 102, 204))
    cta_frame = add_text_overlay(cta_frame, "Ready to Deploy", (960, 350), 
                                (15, 23, 42), 3.5)
    cta_frame = add_text_overlay(cta_frame, "shadowking9021/amd-hackathon:latest", (960, 700), 
                                (15, 23, 42), 1.8)
    for _ in range(fps * 2):
        scenes.append(cta_frame)
    
    # Write frames
    print(f"\nWriting {len(scenes)} frames to video...")
    for i, frame in enumerate(scenes):
        out.write(frame)
        if (i + 1) % 30 == 0:
            print(f"  {i + 1}/{len(scenes)} frames written...")
    
    out.release()
    
    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"\n✓ Video created successfully!")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Duration: {duration}s")
    print(f"  Resolution: 1920x1080")
    print(f"  FPS: {fps}")

if __name__ == "__main__":
    generate_video()
