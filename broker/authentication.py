import jwt
import datetime

from database import DataBase
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

import config

class Authenticator():
    def __init__(self, algorithm: str = None, db_conn: DataBase = None):
        self.db_conn = db_conn
        self.algorithm = algorithm or config.JWT_ALGORITHM
        self.http_bearer = HTTPBearer

    def _generate_jwt(self, username: str) -> str:
        #genera un token jwt contenente l'username e la durata specificata nella configurazione
        payload = {"username" : username, "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=config.JWT_EXP_HOURS)}
        return jwt.encode(payload=payload, key=config.JWT_SECRET, algorithm=self.algorithm)
    
    def register(self, username: str, psw: str) -> tuple[bool, str]:
        return self.db_conn.register_user(username, psw)

    def login(self, username: str, psw: str) -> str:
        #controlla le credenziali nel db e in caso di successo genera e ritorna un token jwt
        login_res = self.db_conn.check_login(username, psw)
        if not login_res:
            return "autenticazione fallita"
        token = self._generate_jwt(username=username)
        return token
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        #verifica la validità del token, e ritorna errore 401 se non è valido 
        token = credentials.credentials
        try:
            decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=[self.algorithm])
            return decoded_token

        except jwt.ExpiredSignatureError as e:
            print(e)
            raise HTTPException(status_code=401, detail="Token scaduto")

        except jwt.InvalidTokenError as e:
            print(e)
            raise HTTPException(status_code=401, detail="Token non valido")
