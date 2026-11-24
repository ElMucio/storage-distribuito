import hashlib
import json
import base64
import asyncio
import httpx
import redis.asyncio as redis 
from fastapi import FastAPI, UploadFile, HTTPException, Depends, Request
from fastapi.responses import Response

import config

from redis_manager import RedisManager
from storage_manager import StorageManager
from authentication import Authenticator
from database import DataBase
from request_models import *

CHUNK_SIZE = config.CHUNK_SIZE
STORAGE_NODES = config.STORAGE_NODES

app = FastAPI()

#inizializzazione client redis
r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB, decode_responses=True)

#inizializzazione dei manager che gestiscono le logiche del sistema
auth_db = DataBase(config.MYSQL_HOST, config.MYSQL_USER, config.MYSQL_PASSWORD, config.MYSQL_DATABASE)
storage_mng = StorageManager(STORAGE_NODES, CHUNK_SIZE)
redis_mng = RedisManager(r)
auth_mng = Authenticator(db_conn=auth_db)



@app.post("/login")
def login(request: LoginRequest):
    #verifica le credenziali e restituisce un JWT
    result = auth_mng.login(request.username, request.psw)
    if result == "autenticazione fallita":
        raise HTTPException(status_code=401, detail="Autenticazione fallita")
    return {"auth_token": result}


@app.post("/register")
def register(request: RegisterRequest):
    #registra un nuovo utente sul database mysql
    res, msg = auth_mng.register(request.username, request.psw)
    if not res:
        raise HTTPException(status_code=401, detail=f"Registrazione fallita: {msg}")
    return 200


async def fetch_chunk(client: httpx.AsyncClient, chunk: dict, username: str):
    #recupera un singolo chunk dai server di storage
    #se il recupero dal server primario fallisce tenta automaticamente con il server di replica
    chunk_name = chunk["chunk_name"]
    primary_server, secondary_server = chunk["servers"]
    order = chunk["order"]

    #url a cui verrà inoltrata la richiesta
    urls = [f"{STORAGE_NODES[primary_server]}/read", f"{STORAGE_NODES[secondary_server]}/read"]
    payload = {"username" : username, "chunk_name": chunk_name}
    
    try:
        #tentativo con il server primario
        resp = await client.post(urls[0], json=payload)
        #genera eccezione se lo status_code non è 2xx
        resp.raise_for_status() 
        return (order, resp.content)
    except httpx.HTTPError:
        #in caso di errore nel recupero del chunk dal primo server prova con il secondo
        try: 
            resp_fallback = await client.post(urls[1], json=payload)
            resp_fallback.raise_for_status() 
            return (order, resp_fallback.content)
        except Exception:
            #se nemmeno il secondo server è in grado di fornire il chunk genera un errore
            print(f"Perdita dati rilevata sul chunk {chunk_name}")
            raise HTTPException(
                status_code=500, 
                detail=f"Impossibile scaricare il file. Frammento '{chunk_name}' irraggiungibile."
            )


@app.get("/list_files")
async def list_files(user: dict = Depends(auth_mng.verify_token)): 
    #restituisce la lista dei file dell'utente
    #Depends(auth_mng.verify_token) blocca la richiesta se il token JWT nell'header non è valido
    username = user["username"]
    #recupera la lista di file corrispondente all'username da redis
    files = await redis_mng.get_file_list(username)
    return {"files": files}


@app.post("/upload")
async def upload_file(file: UploadFile, user: dict = Depends(auth_mng.verify_token)):
    #gestisce l'upload dei file dividendoli in chunk e distribuendoli sui nodi
    #Depends(auth_mng.verify_token) blocca la richiesta se il token JWT nell'header non è valido
    raw_data = await file.read()
    data_len = len(raw_data)
    file_hash = hashlib.sha256(raw_data).hexdigest()

    #ottiene le informazioni necessarie per il salvataggio dei chunk sui nodi di storage
    map = storage_mng.create_upload_map(data_len, file_hash)
    
    successful_writes = [] #tiene traccia dei salbataggi che sono andati a buon fine in caso sia necessario il rollback
    overall_success = True

    #singola sessione http asincrona
    async with httpx.AsyncClient() as c:
        #elabora un chunk alla volta
        for chunk_meta in map:
            #dai dati grezzi ricava un singolo chunk secondo le informazioni fornite dallo storagemanager
            chunk_data = raw_data[chunk_meta["start_byte"] : chunk_meta["end_byte"]]
            encoded_data = base64.b64encode(chunk_data).decode('utf-8') #codifica in base64
            
            tasks = []

            endpoints = []
            
            #prepara le richieste http per inviare il chunk ai nodi di storage
            for node_id in chunk_meta["servers"]:
                base_url = STORAGE_NODES[node_id]
                endpoint = f"{base_url}/write"
                endpoints.append(base_url)
                
                content = {
                    "username": user["username"],
                    "chunk_name": chunk_meta["chunk_name"],
                    "chunk_data": encoded_data
                }
                tasks.append(c.post(endpoint, json=content))

            # attendiamo le risposte dei nodi di storage per il singolo chunk
            results = await asyncio.gather(*tasks, return_exceptions=True)

            chunk_saved = False
            for i, res in enumerate(results):
                # controllo che almeno uno dei nodi sia riuscito a salvare correttamente il file
                if getattr(res, 'status_code', 500) == 200:
                    chunk_saved = True
                    #tracciamo il successo per un eventuale rollback
                    successful_writes.append((endpoints[i], chunk_meta["chunk_name"]))

            if not chunk_saved:
                #nessun nodo ha salvato questo chunk quindi interrompiamo tutto.
                overall_success = False
                break 

        # rollback
        if not overall_success:
            print(f"Upload fallito per {file.filename}. Avvio rollback di {len(successful_writes)} chunk...")
            rollback_tasks = []
            #rimuove i chyunk salvati fino a prima dell'errore
            for base_url, chunk_name in successful_writes:
                payload = {"username": user["username"], "chunk_name": chunk_name}
                rollback_tasks.append(c.post(f"{base_url}/delete", json=payload))
            
            #esegue il rollback in background
            await asyncio.gather(*rollback_tasks, return_exceptions=True)
            
            raise HTTPException(
                status_code=500, 
                detail="Impossibile raggiungere il quorum di scrittura. Upload annullato e orfani rimossi."
            )

    #se l'esecuzione arriva qua significa che ogni chunk è stato salvato su almeno un chunk e possiamo salvare i dati su redis
    await redis_mng.save_upload(user["username"], file_hash, file.filename, data_len, map)
    
    return {"status": "success", "filename": file.filename, "hash": file_hash}


@app.get("/download/{name}")
async def download_file(name: str, user: dict = Depends(auth_mng.verify_token)):
    #scarica un file richiedendo i diversi chunk ai nodi di storage tramite richieste asincrone e poi rimettendoli insieme

    #recupera i metadati del file da redis
    file_details = await redis_mng.get_file_data(user["username"], name)
    if not file_details:
        raise HTTPException(status_code=404, detail="File non trovato")
   
    #download asincrono dei chunk
    async with httpx.AsyncClient() as c:
        #crea una task di download per ogni chunk e le invia tutte
        tasks = [fetch_chunk(c, chunk, user["username"]) for chunk in file_details["chunks"]]
        risultati = await asyncio.gather(*tasks)

    #riordino i chunk (le chiamate asincrone potrebbero non terminare nell'ordine corretto)
    risultati.sort(key=lambda x: x[0])

    #riassemblaggio del file
    file_bytearray = bytearray()
    for _, chunk_data in risultati:
        file_bytearray.extend(chunk_data) 
    
    #invio del file al client 
    return Response(
        content=bytes(file_bytearray),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )

@app.post("/delete")
async def delete_file(request: DeleteRequest, user: dict = Depends(auth_mng.verify_token)):
    #elimina un file gestendo il decremento dei riferimenti e se necessario l'eliminazione dei chunk dai nodi di storage
    username = user["username"]
    #rimuoviamo i collegamenti utente-file su redis e decrementa il refcount, se il refcount è <= 0 ritorna msg == "elimina_file" 
    result, msg, file_details = await redis_mng.delete_file(user["username"], request.filename)

    if not result:
        raise HTTPException(status_code=404, detail="File non trovato")
    
    #necessario eliminare le copie fisiche sui nodi di storage
    if msg == "elimina_file":
        async with httpx.AsyncClient() as c:
            tasks = []
            for chunk in file_details["chunks"]:
                #invia le richieste di eliminazione sia sui server primari che quelli secondari
                primary_server, secondary_server = chunk["servers"]
                urls = [f"{STORAGE_NODES[primary_server]}/delete", f"{STORAGE_NODES[secondary_server]}/delete"]
                payload = {"username": username, "chunk_name" : chunk["chunk_name"]}
 
                tasks.append(c.post(urls[0], json=payload))
                tasks.append(c.post(urls[1], json=payload))

            res = await asyncio.gather(*tasks, return_exceptions=True)

            err = [r for r in res if isinstance(r, Exception) or getattr(r, 'status_code', 500) != 200]
            if len(err) == len(tasks): # segnala errore se tutti i server hanno fallito, altrimenti i collegamenti su redis sono già stati puliti e l'utente non può accedere al file
                raise HTTPException(
                    status_code=500, 
                    detail=f"Errore di pulizia sui server fisici. I metadati sono stati cancellati."
                )

    return {"status_code": 200}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)