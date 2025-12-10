# Use an official Python runtime as a parent image
# We use 3.12 because it is stable for Playwright
FROM python:3.13

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Set working directory
WORKDIR /app

# Install system dependencies required for building tools
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files first (better caching)
COPY pyproject.toml .

# Install Python dependencies
# We assume the project is standard; if you use uv/poetry, adjust accordingly.
# Here we just install the current directory which reads pyproject.toml
RUN pip install --upgrade pip && \
    pip install .

# --- CRITICAL STEP FOR PLAYWRIGHT ---
# 1. Install the playwright library explicitly (if not already in deps)
RUN pip install playwright

# 2. Install Chromium and its SYSTEM dependencies (libraries, fonts, tools)
# "chromium" ensures we don't download Firefox/Webkit (saves space)
# "--with-deps" installs the OS-level libraries Render is missing
RUN playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Expose the port Render will provide
ENV PORT=8080
EXPOSE 8080

# Run the FastMCP server
# We bind to 0.0.0.0 so Render can reach the app
# We explicitly call the CLI to override the 'stdio' in your code
CMD ["sh", "-c", "fastmcp run server.py --transport sse --host 0.0.0.0 --port $PORT"]
