from openai import OpenAI

client = OpenAI(
    api_key="",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

response = client.chat.completions.create(
    model="gemini-3.1-flash-lite",  # or another supported Gemini model
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