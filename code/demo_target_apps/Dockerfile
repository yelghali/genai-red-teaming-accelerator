FROM python:3.11-slim

WORKDIR /app/code/demo_target_apps

# Copy requirements and install dependencies
COPY code/demo_target_apps/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY code/demo_target_apps/http_api_app.py .
COPY code/demo_target_apps/playwright_web_app.py .
COPY code/demo_target_apps/run_demo_apps.py .

# Note: .env will be mounted as volume or passed via environment variables

# Expose ports
EXPOSE 8000 5000

# Run both demo apps
CMD ["python", "run_demo_apps.py"]
