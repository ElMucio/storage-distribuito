# Raccolta in un posto solo di tutti i valori configurabili del broker
# (host, porte, credenziali, chiave JWT).
import os


def _leggi_str(nome, default):
    # legge una variabile d'ambiente come stringa
    return os.environ.get(nome, default)


def _leggi_int(nome, default):
    # legge una variabile d'ambiente e la converte in intero
    # (le env var sono sempre stringhe)
    return int(os.environ.get(nome, default))


REDIS_HOST = _leggi_str("REDIS_HOST", "localhost")
REDIS_PORT = _leggi_int("REDIS_PORT", 6379)
REDIS_DB = _leggi_int("REDIS_DB", 0)

MYSQL_HOST = _leggi_str("MYSQL_HOST", "localhost")
MYSQL_USER = _leggi_str("MYSQL_USER", "storage_distribuito")
MYSQL_PASSWORD = _leggi_str("MYSQL_PASSWORD", "psw_storage_distribuito")
MYSQL_DATABASE = _leggi_str("MYSQL_DATABASE", "storage_distribuito_auth")

JWT_ALGORITHM = _leggi_str("JWT_ALGORITHM", "HS256")
JWT_EXP_HOURS = _leggi_int("JWT_EXP_HOURS", 1)

# Se la JWT_SECRET non e' impostata da fuori, se ne genera una random in automatico.
# In quel caso pero' i token NON sopravvivono al riavvio del broker
# e con piu' broker dietro nginx ognuno firma con una chiave diversa.
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = os.urandom(32).hex()
    print("[config] ATTENZIONE: JWT_SECRET non impostata: ne genero una casuale. "
          "I token non sopravvivono al riavvio del broker.")

CHUNK_SIZE = _leggi_int("CHUNK_SIZE", 1024 * 1024)

# Gli URL degli storage arrivano come unica stringa separata da virgole, quindi
# vanno spezzati in lista. L'ordine conta, il broker li identifica per posizione.
_storage_nodes_raw = _leggi_str("STORAGE_NODES", "http://localhost:8001")
STORAGE_NODES = [s.strip() for s in _storage_nodes_raw.split(",") if s.strip()]
