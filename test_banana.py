import requests
from flask import Flask, request, jsonify
import threading
import os

# ================= CONFIG =================
API_KEY = "ea2b028d7edf04f1e35e99cf6f44928b"
CALLBACK_URL = "https://unhired-dully-bruna.ngrok-free.dev/callback"
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================

app = Flask(__name__)


def generate_image():
    url = "https://api.nanobananaapi.ai/api/v1/nanobanana/generate"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": "A image showing how a bernauli theorem works for a student to understand the concept better.",
        "type": "TEXTTOIAMGE",
        "numImages": 1,
        "image_size": "16:9",
        "callBackUrl": CALLBACK_URL
    }

    response = requests.post(url, json=payload, headers=headers)

    print("Generation request response:")
    print(response.json())


@app.route("/callback", methods=["POST"])
def callback():
    data = request.json

    print("\n📩 Callback received:")
    print(data)

    code = data.get("code")
    info = data.get("data", {}).get("info", {})

    if code == 200:
        image_url = info.get("resultImageUrl")

        if image_url:
            print(f"✅ Image URL: {image_url}")
            download_image(image_url)
    else:
        print("❌ Generation failed")

    return jsonify({"status": "ok"}), 200


def download_image(url):
    print("⬇️ Downloading image...")

    response = requests.get(url, stream=True)
    response.raise_for_status()

    filename = os.path.join(OUTPUT_DIR, "generated.jpg")

    with open(filename, "wb") as f:
        for chunk in response.iter_content(1024):
            f.write(chunk)

    print(f"✅ Image saved as {filename}")


def start_server():
    app.run(port=5000)


if __name__ == "__main__":
    # Start Flask server in background
    threading.Thread(target=start_server).start()

    # Call API
    generate_image()