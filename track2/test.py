import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("FIREWORKS_API_KEY"),
    base_url=os.getenv("FIREWORKS_BASE_URL")
)

response = client.chat.completions.create(
    model="accounts/fireworks/models/kimi-k2p6",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Describe this image in detail. List the objects you see and explain what is happening."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://images.unsplash.com/photo-1582538885592-e70a5d7ab3d3?w=800"
                    }
                }
            ]
        }
    ],
)


print(response.choices[0].message.content)
