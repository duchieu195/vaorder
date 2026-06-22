FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command — override per Cloud Run service
CMD ["python", "-m", "bot.main"]
