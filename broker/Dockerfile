# Creazione dell'immagine Docker del broker (FastAPI).
# Parte da python:3.13-slim e installa le librerie di broker/requirements.txt.
FROM python:3.13-slim

WORKDIR /app

COPY broker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY broker/ .

EXPOSE 8000

CMD ["uvicorn", "broker:app", "--host", "0.0.0.0", "--port", "8000"]
