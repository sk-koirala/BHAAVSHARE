import os
from google import genai
import sys

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        for m in models:
            print(m.name)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
