from flask import Flask, request, jsonify
from tesseract import extract_text
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

@app.route("/ocr", methods=["POST"])
def ocr():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        text = extract_text(file_path)
        return jsonify({"extracted_text": text})
    except Exception as e:
        return jsonify({"error": f"OCR failed: {str(e)}"}), 500

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
