FROM python:3.12-slim

WORKDIR /app

COPY services/lifecycle-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/service-kit/unisora_kit ./unisora_kit
COPY services/lifecycle-service/app ./app

EXPOSE 8004

HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8004/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
