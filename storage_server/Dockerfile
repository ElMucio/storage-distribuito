# In quanto lo storage non necessita du mysql/redis/PyJWT, ed è solo
# un disco con interfaccia REST; installa le librerie di storage_server/requirements.txt
FROM python:3.13-slim

WORKDIR /app

COPY storage_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY storage_server/ .

EXPOSE 8001

CMD ["uvicorn", "storage:app", "--host", "0.0.0.0", "--port", "8001"]
