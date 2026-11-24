# Livello HTTP della GUI: la classe ApiClient parla col broker tramite REST.
# Usa solo urllib, libreria standard.

import json
import os
import urllib.request
import urllib.error
import urllib.parse


class ApiError(Exception):
    # Eccezione unica per tutti gli errori del client:
    #   status = 0    -> errore di rete
    #   status = 4xx  -> il server ha risposto con un errore
    def __init__(self, status, detail):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}" if status else str(detail))


def _messaggio_errore(data):
    # Estrae un messaggio leggibile dal body di errore del broker.
    # FastAPI restituisce {"detail": "..."}
    if not data:
        return ""
    if isinstance(data, bytes):
        try:
            obj = json.loads(data)
            if isinstance(obj, dict) and "detail" in obj:
                return obj["detail"]
        except Exception:
            pass
        try:
            return data.decode("utf-8")
        except Exception:
            return repr(data)
    return str(data)


class ApiClient:
    # Tiene in memoria server_url e token JWT.
    # Tutte le chiamate protette passano l'header Authorization: Bearer token.
    def __init__(self, server_url):
        self.server_url = server_url.rstrip("/")
        self.token = None

    def _chiamata(self, method, path, json_body=None, raw_body=None,
                  content_type=None, auth=False, timeout=120):
        # Helper centralizzato per fare una richiesta HTTP.
        # Cattura HTTPError 4xx/5xx, leggiamo comunque il body. 
        
        headers = {}
        data = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body).encode("utf-8")
        elif raw_body is not None:
            data = raw_body
            if content_type:
                headers["Content-Type"] = content_type
        if auth:
            if not self.token:
                raise ApiError(0, "Non autenticato: serve il login.")
            headers["Authorization"] = "Bearer " + self.token

        req = urllib.request.Request(self.server_url + path, data=data,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except urllib.error.URLError as e:
            raise ApiError(0, f"Impossibile contattare il server: {e.reason}")
        except TimeoutError:
            raise ApiError(0, "Timeout: il server non risponde.")


    def login(self, username, password):
        # POST /login -> salva il token JWT restituito dal broker
        status, data = self._chiamata("POST", "/login",
            json_body={"username": username, "psw": password})
        if status != 200:
            raise ApiError(status, _messaggio_errore(data))
        self.token = json.loads(data).get("auth_token")
        if not self.token:
            raise ApiError(0, "Risposta del server senza token.")

    def register(self, username, password):
        # POST /register -> crea un nuovo utente nel database del broker
        status, data = self._chiamata("POST", "/register",
            json_body={"username": username, "psw": password})
        if status not in (200, 201):
            raise ApiError(status, _messaggio_errore(data))

    def logout(self):
        # Cancella il token in memoria.
        self.token = None

    def list_files(self):
        # GET /list_files -> elenco dei file dell'utente loggato
        status, data = self._chiamata("GET", "/list_files", auth=True)
        if status != 200:
            raise ApiError(status, _messaggio_errore(data))
        return json.loads(data).get("files", [])

    def upload(self, filename, content_bytes):
        # POST /upload con multipart/form-data

        # Preveniamo il rischio che il delimitatore si confonda accidentalmente
        # con il testo o i dati del file che stai inviando
        boundary = "----guiboundary" + os.urandom(8).hex()
        safe_name = filename.replace('"', "")
        body = (
            ("--" + boundary + "\r\n").encode() +
            f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'.encode("utf-8") +
            b"Content-Type: application/octet-stream\r\n\r\n" +
            content_bytes +
            ("\r\n--" + boundary + "--\r\n").encode()
        )
        status, data = self._chiamata("POST", "/upload", raw_body=body,
            content_type="multipart/form-data; boundary=" + boundary, auth=True)
        if status != 200:
            raise ApiError(status, _messaggio_errore(data))
        return json.loads(data)

    def download(self, filename):
        # GET /download/nome_file. Il filename viene URL-encoded
        # per resistere a spazi, accenti e barre.
        encoded = urllib.parse.quote(filename, safe="")
        status, data = self._chiamata("GET", "/download/" + encoded, auth=True)
        if status != 200:
            raise ApiError(status, _messaggio_errore(data))
        return data

    def delete(self, filename):
        # POST /delete con il nome del file nel body JSON
        status, data = self._chiamata("POST", "/delete",
            json_body={"filename": filename}, auth=True)
        if status != 200:
            raise ApiError(status, _messaggio_errore(data))
