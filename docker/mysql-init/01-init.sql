-- Script eseguito da MySQL al PRIMO avvio del container
-- Crea la tabella degli utenti del broker.
-- Lunghezze fisse:
--   password_hash CHAR(64) = SHA-256 in esadecimale (sempre 64 caratteri)
--   salt          CHAR(32) = 16 byte casuali in esadecimale (sempre 32)
USE storage_distribuito_auth;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash CHAR(64) NOT NULL,
    salt CHAR(32) NOT NULL
);
