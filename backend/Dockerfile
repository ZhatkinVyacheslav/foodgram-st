
FROM python:3.12

WORKDIR /app

COPY requirements.txt /app/
RUN \
    python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir gunicorn==20.1.0 && \
    python3 -m pip install --no-cache-dir -r requirements.txt

COPY . /app
CMD ["gunicorn", "foodgram_backend.wsgi", "--bind", "0:8000"]
