# Storage distribuito

> **EN** — Distributed file storage built for a university course on Parallel and Distributed Systems.
> Files are split into 1 MiB chunks, replicated on two storage nodes and deduplicated by SHA-256;
> two FastAPI brokers behind nginx provide high availability, with JWT auth, MySQL and Redis.
> Eight containers orchestrated with Docker Compose.

> Progetto del corso di **Sistemi Paralleli e Distribuiti** — Università degli Studi di Perugia, A.A. 2025/2026  
> Realizzato in collaborazione da [Leonardo Bordini](https://github.com/leonardobordini) e [Luca Sonno](https://github.com/ElMucio)

---

## 📌 Descrizione

Sistema di storage distribuito sviluppato per il corso di Sistemi Paralleli e Distribuiti.

Permette a più utenti, dopo aver effettuato registrazione e login, di caricare e scaricare file in modo trasparente. Dietro le quinte i file vengono frammentati in chunk da 1 MiB, replicati su due nodi distinti e deduplicati per evitare di archiviare due volte lo stesso contenuto.

### Architettura

Il sistema è composto da otto container orchestrati con `docker compose`.

Solo `nginx` espone una porta verso l'host, la `8000`. Tutti gli altri container comunicano solo all'interno della rete privata di Docker.

### Funzionalità

- Registrazione e login con autenticazione **JWT** (HS256, scadenza 1h).
- Password salate con SHA-256.
- Upload di file con frammentazione, replica round-robin su due storage diversi e deduplicazione content-addressed (SHA-256 + reference counting).
- Download con failover automatico: se uno storage non risponde, il broker recupera i chunk dalle repliche secondarie.
- Lista dei file dell'utente.
- Cancellazione dei file con garbage collection automatica dei chunk fisici quando il `ref_count` arriva a 0.
- Alta disponibilità del coordinatore: due broker dietro nginx; se uno cade, l'altro continua a servire le richieste.
- Load balancing round-robin delle richieste fra i due broker.
- GUI desktop in Tkinter per gli utenti finali.

---

## 🛠 Requisiti tecnici

- Linguaggio/i utilizzato/i: Python
- Ambiente di sviluppo: Docker Desktop oppure Docker Engine 20.10+ con docker compose v2; Python 3.10+ solo se si vuole usare la GUI client.
- Eventuali librerie/framework/middleware richiesti: FastAPI, Uvicorn, Pydantic, httpx + asyncio, mysql-connector-python, redis (async), PyJWT, nginx 1.27-alpine, MySQL 8.0, Redis 7.4-alpine, Tkinter, Docker Compose.
- Modalità di esecuzione: 
    ### Avvio rapido

    #### 1. Crea il file `.env`

    Parti dal modello e modifica le credenziali a piacere.

    Su Windows:

    ```bash
    copy .env.example .env
    ```

    Su Linux / macOS:

    ```bash
    cp .env.example .env
    ```

    #### 2. Avvia il sistema

    ```bash
    docker compose up -d
    ```

    #### 3. Verifica lo stato dei container

    ```bash
    docker compose ps
    ```

    Dovresti vedere tutti gli 8 container in stato `running`.

    #### 4. Avvio iniziale

    Il primo avvio può richiedere qualche minuto, perché Docker deve scaricare le immagini base e costruire quelle di broker e storage.

    Dalle volte successive l'avvio sarà molto più rapido.

    A questo punto il sistema risponde su:

    ```text
    http://localhost:8000
    ```

    Le richieste passano da nginx e vengono distribuite fra i broker.

    ### Utilizzo

    #### GUI desktop

    Da terminale:

    ```bash
    python client_gui/app.py
    ```

    Si apre una finestra Tkinter con:

    - schermata di login / registrazione;
    - campo "Server" preimpostato a `http://localhost:8000`;
    - schermata File con elenco dei propri file;
    - bottoni Aggiorna, Upload, Download, Elimina e Logout;
    - possibilità di scaricare un file con doppio click dalla lista.

    La GUI usa solo la libreria standard di Python (`tkinter` + `urllib`), quindi non serve nessun `pip install`.

    #### REST API

    Le REST API possono essere provate con strumenti come `curl` o Postman.

    | Endpoint | Verbo | Body | Auth |
    |---|---|---|---|
    | `/register` | POST | `{"username": "...", "psw": "..."}` | no |
    | `/login` | POST | `{"username": "...", "psw": "..."}` | no, restituisce JWT |
    | `/list_files` | GET | - | sì |
    | `/upload` | POST | multipart/form-data, campo `file` | sì |
    | `/download/<nome>` | GET | - | sì |
    | `/delete` | POST | `{"filename": "..."}` | sì |

    L'autenticazione si fa tramite header:

    ```text
    Authorization: Bearer <jwt>
    ```

    Dove `<jwt>` è il valore di `auth_token` restituito da `/login`.

- Virtualizzazione: il progetto prevede l'utilizzo di Docker Compose con otto container.

### Prerequisiti

- **Docker Desktop** oppure **Docker Engine 20.10+** con **docker compose v2**.
- **Python 3.10+**, solo se si vuole usare la GUI client. Il sistema in sé gira tutto in Docker.
- Porta `8000` libera sull'host.



### Tecnologie usate

| Componente | Libreria / Tecnologia |
|---|---|
| Web framework | FastAPI |
| Server ASGI | Uvicorn |
| Validazione input | Pydantic |
| HTTP client asincrono broker -> storage | httpx + asyncio |
| Driver MySQL | mysql-connector-python |
| Driver Redis | redis (async) |
| JWT | PyJWT |
| Reverse proxy + load balancer | nginx 1.27-alpine |
| Database utenti | MySQL 8.0 |
| Database metadati | Redis 7.4-alpine |
| GUI desktop | Tkinter |
| Orchestrazione | Docker Compose |

### Struttura del progetto

```text
progetto_sistemi-main/
├── docker-compose.yml          gestione degli 8 container
├── .env.example                modello del file .env
├── .gitignore
├── .dockerignore
├── requirements.txt            riferimento globale per sviluppo locale
├── broker/                     servizio coordinatore (FastAPI)
│   ├── Dockerfile
│   ├── broker.py               endpoint REST principali
│   ├── config.py               variabili d'ambiente
│   ├── database.py             interfaccia MySQL per gli utenti
│   ├── authentication.py       JWT
│   ├── redis_manager.py        metadati su Redis
│   ├── storage_manager.py      logica di chunking e replica
│   ├── request_models.py       schemi Pydantic
│   └── requirements.txt
├── storage_server/             nodo di storage (FastAPI)
│   ├── Dockerfile
│   ├── storage.py              endpoint write/read/delete/register
│   ├── request_models.py
│   └── requirements.txt
├── client_gui/                 GUI desktop in Tkinter
│   ├── api.py                  livello HTTP client
│   └── app.py                  finestra principale e schermate
├── client/                     prova end-to-end da riga di comando (python client/client.py)
│   └── client.py
└── docker/
    ├── nginx/nginx.conf        reverse proxy e load balancer
    └── mysql-init/01-init.sql  crea la tabella users al primo avvio
```

### Comandi utili

Vedere lo stato dei container:

```bash
docker compose ps
```

Seguire i log di un servizio in tempo reale:

```bash
docker compose logs -f broker1
```

Riavviare un singolo servizio, ad esempio dopo una modifica al codice:

```bash
docker compose restart broker1
```

Spegnere il sistema mantenendo i dati nei volumi:

```bash
docker compose down
```

Spegnere il sistema e cancellare completamente i dati:

```bash
docker compose down -v
```

> Attenzione: questo comando cancella anche utenti registrati, file caricati e metadati.

Entrare in una shell dentro un container:

```bash
docker compose exec storage1 sh
```

### Note e troubleshooting

#### Il sistema non parte: `MYSQL_PASSWORD is not set`

Significa che manca il file `.env`.

Per risolvere, crea il file `.env` copiando `.env.example`, come indicato nella sezione di avvio rapido.

#### Cambio password nel `.env` senza effetto

L'immagine ufficiale di MySQL legge le variabili d'ambiente solo al primo avvio, quando il volume è vuoto.

Per applicare nuove credenziali:

```bash
docker compose down -v
docker compose up -d
```

> Attenzione: `docker compose down -v` cancella anche utenti registrati e file caricati.

#### Porta `8000` già in uso

Modifica nel file `docker-compose.yml`, nella sezione `nginx`, la riga:

```yaml
"8000:80"
```

Ad esempio, puoi cambiarla in:

```yaml
"8080:80"
```

In questo caso il sistema risponderà su:

```text
http://localhost:8080
```

#### La GUI non si apre su Linux senza display grafico

Tkinter richiede un server grafico X.

Su server headless conviene usare direttamente le REST API.

---

Licenza [MIT](LICENSE).
