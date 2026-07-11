"""Test if thinking is disabled in API response."""

import os
import base64
import sys

import cv2
from openai import OpenAI

# Load env
from dotenv import load_dotenv
load_dotenv()

api_key = os.environ.get("FIREWORKS_API_KEY")
base_url = os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
model = os.environ.get("ALLOWED_MODELS", "accounts/fireworks/models/qwen3-vl-8b-instruct").split(",")[0].strip()

client = OpenAI(api_key=api_key, base_url=base_url)

# Extract a test frame from a simple test video or use a dummy image
print(f"Testing API with model: {model}", file=sys.stderr)
print(f"Base URL: {base_url}", file=sys.stderr)

# Create a simple test image (100x100 red square)
import numpy as np
test_image = np.zeros((100, 100, 3), dtype=np.uint8)
test_image[:, :] = [0, 0, 255]  # Red

ok, buf = cv2.imencode(".jpg", test_image)
if not ok:
    print("Failed to encode test image", file=sys.stderr)
    sys.exit(1)

frame_b64 = base64.b64encode(buf).decode()

# Call API with thinking disabled
print("\n=== Calling API with thinking DISABLED ===", file=sys.stderr)
resp = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in one sentence."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}},
            ],
        }
    ],
    temperature=0.7,
    max_tokens=256,
    timeout=25,
    extra_body={"thinking": {"type": "disabled"}},
)

print("\n--- Full Response Object ---")
print(f"Type: {type(resp)}")
print(f"Dir: {[x for x in dir(resp) if not x.startswith('_')]}")

print("\n--- Response Choices[0] ---")
choice = resp.choices[0]
print(f"Type: {type(choice)}")
print(f"Dir: {[x for x in dir(choice) if not x.startswith('_')]}")

print("\n--- Message ---")
message = choice.message
print(f"Type: {type(message)}")
print(f"Dir: {[x for x in dir(message) if not x.startswith('_')]}")
print(f"Content: {message.content[:100]}...")

# Check for reasoning field
if hasattr(message, 'reasoning'):
    print(f"\n✅ REASONING FIELD FOUND!")
    print(f"Reasoning: {message.reasoning[:200] if message.reasoning else 'None'}")
else:
    print(f"\n✅ NO REASONING FIELD (thinking is disabled)")

# Check for other fields
print(f"\n--- All Message Fields ---")
for attr in dir(message):
    if not attr.startswith('_'):
        val = getattr(message, attr)
        if not callable(val):
            print(f"{attr}: {str(val)[:80]}...")
