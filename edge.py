import edge_tts
import asyncio
import os

# Preserved your exact button format
VOICE_MAP = {
    "English": {"Male": "en-US-ChristopherNeural", "Female": "en-US-AriaNeural"},
    "German": {"Male": "de-DE-ConradNeural", "Female": "de-DE-KatjaNeural"},
    "Hindi": {"Male": "hi-IN-MadhurNeural", "Female": "hi-IN-SwaraNeural"},
    "Japanese": {"Male": "ja-JP-KeitaNeural", "Female": "ja-JP-NanamiNeural"},
    "Spanish": {"Male": "es-ES-AlvaroNeural", "Female": "es-ES-ElviraNeural"}
}

# Language to Tesseract code mapping
LANG_TO_TESSERACT = {
    "English": "eng",
    "German": "deu",
    "Hindi": "hin",
    "Japanese": "jpn",
    "Spanish": "spa"
}

async def generate_tts(
    text: str,
    language: str,
    gender: str,
    output_path: str
) -> str:
    """TTS generation with your exact format"""
    try:
        # Get voice from your format
        voice = VOICE_MAP.get(language, {}).get(gender)
        if not voice:
            voice = VOICE_MAP["English"]["Male"]  # Fallback
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate="+10%",  # Slightly faster speech
            pitch="+0Hz"
        )
        
        await communicate.save(output_path)
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
            raise RuntimeError("Empty TTS output")
            
        return output_path
    except Exception as e:
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise RuntimeError(f"TTS generation failed: {str(e)}")