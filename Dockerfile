# Use an official, stable, and lightweight Python image
FROM python:3.11-slim

# Set environment variables to optimize Python runtime in Docker
# Prevents Python from writing .pyc files to disk and buffers streams for live logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install basic system utilities and curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application directories and files into the container
COPY config/ ./config/
COPY services/ ./services/
COPY llm/ ./llm/
COPY app.py .

# Create the standard operational directories used for file processing
RUN mkdir -p output uploads report/un_filtered_report

# Expose the default Streamlit network port
EXPOSE 8501

# Add a health check to monitor Streamlit server availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Command to run the Streamlit web server, binding to all interfaces
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
