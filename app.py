import os
from flask import Flask, request, jsonify, render_template, send_file
import openai
import sqlite3
import requests
from io import BytesIO

app = Flask(__name__)

# === Replace these with your actual API keys ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Change to your preferred voice ID

openai.api_key = OPENAI_API_KEY
DB_PATH = "innersense.db"


# === Initialize SQLite database ===
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mood TEXT NOT NULL,
                transcript TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )


# === Routes ===
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/meditate", methods=["POST"])
def meditate():
    mood = request.json.get("mood")
    if not mood:
        return jsonify({"error": "Mood not provided"}), 400

    prompt = f"Guide me through a calming 3-minute meditation for someone feeling {mood}. Use peaceful and reassuring language."

    try:
        # Generate script
        response = openai.ChatCompletion.create(
            model="gpt-4", messages=[{"role": "user", "content": prompt}]
        )
        meditation_text = response["choices"][0]["message"]["content"]

        # Convert to voice
        audio_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": meditation_text,
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.7},
            },
        )

        if audio_response.status_code != 200:
            return jsonify({"error": "Voice generation failed"}), 500

        # Save session
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO sessions (mood, transcript) VALUES (?, ?)",
                (mood, meditation_text),
            )

        return send_file(BytesIO(audio_response.content), mimetype="audio/mpeg")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history", methods=["GET"])
def history():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT mood, transcript, created_at FROM sessions ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
    return jsonify(rows)


# === Start App ===
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
