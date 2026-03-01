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

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Clone and build the Google Custom Search MCP server
RUN git clone https://github.com/Frostedpilot/mcp-google-custom-search-server.git \
    mcp_servers/mcp-google-custom-search-server \
    && cd mcp_servers/mcp-google-custom-search-server \
    && npm install \
    && npm run build

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
