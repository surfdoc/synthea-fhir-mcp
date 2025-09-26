FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Expose HTTP/SSE default port (8080 for Cloud Run)
EXPOSE 8080

# Cloud Run sets the PORT environment variable
ENV PORT=8080

# Run the Synthea FHIR MCP server
CMD [ "python", "src/synthea_server.py" ]
