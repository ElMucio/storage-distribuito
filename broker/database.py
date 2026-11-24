import mysql.connector
import hashlib
import os

class DataBase():
    def __init__(self, host: str, user: str, psw: str, database: str):
        try: #connessione al db
            self._db = mysql.connector.connect(
                host=host,
                user=user,
                password=psw,
                database=database,
                autocommit=True
            )
            self._cursor = self._db.cursor(buffered=True) 
        except Exception as e:
            print(f"Errore nella connessione al database: {str(e)}")


    #genera un hash SHA256 della password + salt
    def _hash_psw(self, psw: str, salt: str) -> str:
        return hashlib.sha256((psw + salt).encode('utf-8')).hexdigest()
    
    #controlla se l'username scelto è già preso
    def _check_username_taken(self, username: str) -> bool:
        query = "SELECT id FROM users WHERE username = %s"
        self._cursor.execute(query, (username,))
        return self._cursor.fetchone() is not None
    
    #registra un nuovo utente controllando prima se l'username è già preso tramite _check_username_taken
    def register_user(self, username: str, password: str) -> tuple[bool, str]:
        if self._check_username_taken(username):
            return False, "Username già in uso."

        salt = os.urandom(16).hex() #genera il salt usato per l'hash della password
        hashed_psw = self._hash_psw(password, salt)

        try:
            #inserisce la nuova riga nel database
            query = "INSERT INTO users (username, password_hash, salt) VALUES (%s, %s, %s)"
            self._cursor.execute(query, (username, hashed_psw, salt))
            self._db.commit()
            return True, "Registrazione effettuata"
        except Exception as e:
            return False, f"Errore durante la registrazione: {str(e)}"
    
    def check_login(self, username: str, password: str) -> bool:
        #richiede l'hash della password e il salt dell'username specificato
        query = "SELECT password_hash, salt FROM users WHERE username = %s"
        self._cursor.execute(query, (username,))
        result = self._cursor.fetchone()
        
        if result:
            db_hash, db_salt = result
            #confronta gli hash della password
            return self._hash_psw(password, db_salt) == db_hash
        
        return False

    
