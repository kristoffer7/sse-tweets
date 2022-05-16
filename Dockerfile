FROM python:3.10-slim-bullseye

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8080
CMD ["uvicorn", "sse_twitter.app:app", "--host", "0.0.0.0", "--port", "8080"]
