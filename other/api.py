from flask import Flask, request, send_file, jsonify
import asyncio
import os
from edge import generate_tts  # Importing from edge.py

app = Flask(__name__)

@app.route('/tts', methods=['POST'])
def tts_api():
    try:
        data = request.get_json()  # Ensure JSON input
        text = data.get("text")
        language = data.get("language", "English (US)")
        gender = data.get("gender", "Male")

        if not text:
            return jsonify({"error": "Text is required"}), 400

        output_file = "output.mp3"

        # Run TTS asynchronously
        asyncio.run(generate_tts(text, language, gender, output_file))

        # Ensure the file exists before sending
        if os.path.exists(output_file):
            return send_file(output_file, as_attachment=True)
        else:
            return jsonify({"error": "TTS generation failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
