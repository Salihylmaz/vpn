# Python tabanlı imaj (slim yerine tam, uyumluluk için)
FROM python:3.10

WORKDIR /app

# Gereksinimleri kopyala
COPY requirements.txt .

# Torch CPU-only wheel + transformers + FastAPI + Uvicorn
RUN pip install --no-cache-dir -r requirements.txt -f https://download.pytorch.org/whl/torch_stable.html

# Kodları kopyala
COPY . .

# Uygulama 8000 portunda çalışacak
EXPOSE 8000

# FastAPI başlatma komutu
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
