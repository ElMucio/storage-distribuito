
class StorageManager:
    def __init__(self, nodes: list[str], chunk_size: int):
        self.nodes = nodes
        self.nodes_num = len(nodes)
        self.chunk_size = chunk_size

    def create_upload_map(self, data_len: int, file_hash: str) -> list[dict]:
        #Ritorna una lista che contiene le informazioni necessarie al salvataggio dei vari chunk
        map = []
        for i in range(0, data_len, self.chunk_size):
            chunk_index = i // self.chunk_size #calcola l'indice del chunk
            
            primary = chunk_index % self.nodes_num
            secondary = (chunk_index + 1) % self.nodes_num
            
            #aggiunge le informazioni necessarie al salvataggio del singolo chunk
            map.append({
                "chunk_name": f"{file_hash}_part{chunk_index}",
                "order": chunk_index,
                "start_byte": i,
                "end_byte": i + self.chunk_size,
                "servers": [primary, secondary]
            })
        return map

