import redis, json

class RedisManager:
    def __init__(self, redis_client: redis.Redis):
        self.r = redis_client

    async def save_upload(self, owner: str, file_hash: str, filename: str, file_size: int, map: list[dict]):
        #salva i metadati del file da caricare e gestisce la deduplicazione: se un file è stato caricato da due utenti diversi 
        #viene salvato una volta sola e viene incrementato il ref_count per il file

        #struttura i dati dei singoli chunk in cui è diviso il file
        chunks_data = [
            {"chunk_name": entry["chunk_name"], "order": entry["order"], "servers": entry["servers"]}
            for entry in map
        ]


        redis_data = {
            "hash": file_hash,
            "name": filename,
            "file_size": file_size,
            "chunk_num": len(chunks_data),
            "chunks": chunks_data
        }

        #no duplicazione file uguali anche se di utenti diversi
        exists = await self.r.exists(f"file:{file_hash}")   
        if not exists:
            await self.r.set(f"file:{file_hash}", json.dumps(redis_data))
        #incrementa il ref_count 
        await self.r.incr(f"file:{file_hash}:ref_count")
        #aggiunge il nuovo file al set dei file per il determinato utente
        await self.r.sadd(f"index:owner:{owner}:files", filename)
        #crea un nuovo indice per mappare il nome del file dell'utente all'hash
        await self.r.set(f"index:owner:{owner}:name:{filename}", file_hash)

        
    async def get_file_data(self, owner: str, filename: str) -> dict:
        #recupera i dettagli di un file a partire da owner e filename

        #cerca l'hash associato al file del determinato utente
        hashes_found = await self.r.get(f"index:owner:{owner}:name:{filename}")
        if not hashes_found:
            return None
        
        if isinstance(hashes_found, bytes):
            hashes_found = hashes_found.decode('utf-8')
        
        #recupera le informazioni del file dato l'hash e le ritorna in json
        file_details_raw = await self.r.get(f"file:{hashes_found}")
        return json.loads(file_details_raw)
    
    async def get_file_list(self, owner: str) -> list:
        #ritorna la lista dei file di un determinato owner
        files_set = await self.r.smembers(f"index:owner:{owner}:files")
        return list(files_set)
    
    async def delete_file(self, owner: str, filename: str):
        #gestisce la cancellazione dei file decrementando il ref_count e se raggiunge zero comunica di eliminare la copia del file sui server di storage
        
        file_details = await self.get_file_data(owner, filename)
        if not file_details:
            return False, "file non trovato", {}
        
        file_hash = file_details["hash"] 

        #decrementa il ref_count
        new_ref_count = await self.r.decr(f"file:{file_hash}:ref_count")
        
        #rimuove il file dagli indici dell'utente
        await self.r.srem(f"index:owner:{owner}:files", filename)
        await self.r.delete(f"index:owner:{owner}:name:{filename}")

        if new_ref_count <= 0:
            #se il ref_count è minore o uguale di zero significa che nessun utente necessita del file
            #elimina i metadati del file e il contatore
            await self.r.delete(f"file:{file_hash}")
            await self.r.delete(f"file:{file_hash}:ref_count")
            #comunica di eliminare la copia sui server di storage, ritorna i metadati del file per sapere a quali
            #server di storage inviare la richiesta di eliminazione dei chunk
            return True, "elimina_file", file_details
        else:
            return True, "mantieni_file", {}