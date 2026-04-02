# Use an official Python runtime as a parent image
FROM python:3.11-slim 

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    -- no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install uvicorn and gunicorn for running the FastAPI app
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt 
    
# Clean up unnecessary files and packages
COPY . .


# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000


# Expose the port that the FastAPI app will run on    
EXPOSE 8000


# Add a health check to ensure the container is running properly
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

    
# Run the FastAPI app using uvicorn with multiple workers for better performance
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]