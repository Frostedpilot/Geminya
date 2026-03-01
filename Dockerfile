FROM python:3.11-slim

# System dependencies: ffmpeg (Spotify audio), git (librespot pip install), Node.js (MCP servers via npx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies line-by-line (order matters, most critical last)
COPY requirements.txt .
RUN grep -v '^\s*#' requirements.txt | grep -v '^\s*$' | while read -r pkg; do \
        pip install --no-cache-dir "$pkg" || true; \
    done

# Copy application code
COPY . .

# Create logs directory and make app writable for non-root user
RUN mkdir -p logs \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app

# HF Spaces runs containers as uid 1000
USER appuser

# HF Spaces expects port 7860
EXPOSE 7860

# Set environment marker for keep-alive server
ENV KEEP_ALIVE=1

CMD ["python", "start_nigler.py"]
