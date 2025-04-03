from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio
import logging
import time
import hashlib
from tesseract import extract_text
from edge import generate_tts
from typing import Optional

app = FastAPI(docs_url=None, redoc_url=None)

# Balanced CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600
)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    gender: str = "male"

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/ocr")
async def ocr_endpoint(
    image: UploadFile = File(...),
    language: str = Query("eng+hin", description="Language code(s). For Hindi use 'hin', for English use 'eng', or combine with '+'")
):
    """Memory-optimized OCR with multi-language support"""
    temp_path = None
    try:
        # Create temp file with hashed name
        file_hash = hashlib.md5()
        temp_path = f"{UPLOAD_FOLDER}/ocr_{int(time.time())}_{file_hash.hexdigest()[:8]}.tmp"
        
        # Stream to disk in chunks (memory efficient)
        with open(temp_path, "wb") as f:
            while chunk := await image.read(8192):  # 8KB chunks
                file_hash.update(chunk)
                f.write(chunk)
        
        # Process with timeout
        try:
            with open(temp_path, "rb") as f:
                text = await asyncio.wait_for(
                    asyncio.to_thread(extract_text, f.read(), language),
                    timeout=30.0  # Increased timeout for multi-language
                )
            return {"extracted_text": text}
        except asyncio.TimeoutError:
            raise HTTPException(408, "OCR processing timeout")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"OCR Error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"OCR processing failed: {str(e)}")
    finally:
        # Ensure cleanup
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logging.warning(f"Failed to cleanup temp file: {str(e)}")

@app.post("/tts")
async def tts_endpoint(
    background_tasks: BackgroundTasks,
    request: TTSRequest
):
    """Optimized TTS with caching"""
    try:
        if len(request.text) > 5000:
            raise HTTPException(400, "Text exceeds 5000 characters")
        
        # Create consistent filename based on content
        file_hash = hashlib.md5(f"{request.text}{request.language}{request.gender}".encode()).hexdigest()
        output_file = f"/tmp/tts_{file_hash}.mp3"
        
        # Return cached version if exists
        if os.path.exists(output_file):
            return FileResponse(
                output_file,
                media_type="audio/mpeg",
                filename="speech.mp3"
            )
        
        # Process with timeout
        try:
            await asyncio.wait_for(
                generate_tts(request.text, request.language, request.gender, output_file),
                timeout=20.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(408, "TTS generation timeout")
        
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            raise HTTPException(500, "Empty TTS output")
        
        # Schedule cleanup after 1 hour
        async def delayed_cleanup():
            await asyncio.sleep(3600)
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except Exception as e:
                logging.warning(f"Cleanup failed: {str(e)}")
                
        background_tasks.add_task(delayed_cleanup)
        
        return FileResponse(
            output_file,
            media_type="audio/mpeg",
            filename="speech.mp3"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"TTS Error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"TTS processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        workers=1,
        limit_max_requests=200,
        timeout_keep_alive=30,
        log_level="warning",
        loop="asyncio",
        reload=False
    )
