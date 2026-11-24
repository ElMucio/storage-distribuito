import os
import base64
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from request_models import *

DATA_DIR = os.environ.get("DATA_DIR", "data")
PORT = int(os.environ.get("PORT", 8001))
HOST = os.environ.get("STORAGE_HOST", "0.0.0.0")
BASE_DATA_DIR = os.path.join(os.getcwd(), DATA_DIR)


def init() -> bool:
    if not os.path.exists(BASE_DATA_DIR):
        try:
            os.mkdir(BASE_DATA_DIR)
            return True
        except Exception as e:
            print(f"Errore nella creazione della cartella di storage: {str(e)}")
            return False
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not init():
        print("Errore nell'inizializzazione del nodo di storage")
    yield

# lifespan di diviide in due punti, pre e post avvio, per avviare init tranquillamente

app = FastAPI(lifespan=lifespan)

@app.post("/write")
async def write_chunk(request: WriteRequest):
    try:
        user_dir = os.path.join(BASE_DATA_DIR, request.username)
        os.makedirs(user_dir, exist_ok=True) 

        file_path = os.path.join(user_dir, request.chunk_name)
        raw_bytes = base64.b64decode(request.chunk_data)
        
        with open(file_path, "wb") as f:
            f.write(raw_bytes)
            
        return {"status": "ok", "chunk_name": request.chunk_name, "bytes_written": len(raw_bytes)}

    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Errore di scrittura su disco: {str(e)}")


@app.post("/delete")
async def delete_chunk(request: DeleteRequest):
    file_path =  os.path.join(BASE_DATA_DIR, request.username, request.chunk_name)
    if not os.path.exists(file_path):   
        raise HTTPException(status_code=404, detail="Chunk non trovato su questo nodo")
    
    try:
        os.remove(file_path)
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Errore di cancellazione disco: {str(e)}")
    
    return 200

@app.post("/read")
async def read_chunk(request: ReadRequest):
    file_path = os.path.join(BASE_DATA_DIR, request.username, request.chunk_name)
    if not os.path.exists(file_path):   
        raise HTTPException(status_code=404, detail="Chunk non trovato su questo nodo")

    return FileResponse(file_path, media_type="application/octet-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)