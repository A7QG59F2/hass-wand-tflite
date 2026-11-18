FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir "ai-edge-litert==2.3.0" "numpy<3"

COPY server.py /app/server.py

EXPOSE 8000
CMD ["python3", "/app/server.py"]
