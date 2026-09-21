FROM python:3.11-slim

WORKDIR /app

RUN useradd \
    --uid 10001 \
    --create-home \
    --shell /usr/sbin/nologin \
    linkguard

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

USER 10001

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]