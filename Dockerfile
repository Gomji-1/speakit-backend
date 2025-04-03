FROM python:3.10-slim-bullseye

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    OMP_THREAD_LIMIT=1

# Set Tesseract config
ENV TESSERACT_CMD=/usr/bin/tesseract \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-san \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download additional language files (best quality)
RUN wget -q -P ${TESSDATA_PREFIX} \
    https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata && \
    wget -q -P ${TESSDATA_PREFIX} \
    https://github.com/tesseract-ocr/tessdata_best/raw/main/hin.traineddata && \
    wget -q -P ${TESSDATA_PREFIX} \
    https://github.com/tesseract-ocr/tessdata_best/raw/main/san.traineddata && \
    wget -q -P ${TESSDATA_PREFIX} \
    https://github.com/tesseract-ocr/tessdata_best/raw/main/osd.traineddata

# Set working directory
WORKDIR /app

# Copy only necessary files
COPY requirements.txt .
COPY server_fastapi.py .
COPY tesseract.py .
COPY edge.py .

# Install Python dependencies
RUN pip install --no-cache-dir "numpy<2" && \
    pip install --no-cache-dir -r requirements.txt

# Create uploads directory
RUN mkdir -p /tmp/uploads && chmod 777 /tmp/uploads

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Run FastAPI with optimized settings
CMD ["uvicorn", "server_fastapi:app", \
    "--host", "0.0.0.0", \
    "--port", "5000", \
    "--workers", "1", \
    "--limit-concurrency", "20", \
    "--timeout-keep-alive", "30"]
