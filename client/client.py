# Script di prova da riga di comando: esegue il ciclo completo
# registrazione -> login -> upload -> lista -> download (con verifica) -> cancellazione.
# Uso: python client/client.py [--server http://127.0.0.1:8000] [--utente demo] [--password demo]
import argparse

import httpx

NOME_FILE = "file_di_prova.txt"
CONTENUTO = ("Contenuto di prova per lo storage distribuito.\n" * 2000).encode()


def main():
    parser = argparse.ArgumentParser(description="Prova end-to-end dello storage distribuito")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--utente", default="demo")
    parser.add_argument("--password", default="demo")
    args = parser.parse_args()

    with httpx.Client(base_url=args.server, timeout=30) as client:
        credenziali = {"username": args.utente, "psw": args.password}

        # la registrazione fallisce se l'utente esiste gia': in quel caso si prosegue col login
        res = client.post("/register", json=credenziali)
        print("register:", res.status_code, res.text)

        res = client.post("/login", json=credenziali)
        res.raise_for_status()
        headers = {"Authorization": f"Bearer {res.json()['auth_token']}"}

        res = client.post("/upload", headers=headers,
                          files={"file": (NOME_FILE, CONTENUTO, "text/plain")})
        print("upload:", res.status_code, res.text)

        res = client.get("/list_files", headers=headers)
        print("list_files:", res.status_code, res.text)

        res = client.get(f"/download/{NOME_FILE}", headers=headers)
        integro = res.status_code == 200 and res.content == CONTENUTO
        print("download:", res.status_code, "contenuto integro" if integro else "CONTENUTO DIVERSO")

        res = client.post("/delete", headers=headers, json={"filename": NOME_FILE})
        print("delete:", res.status_code, res.text)


if __name__ == "__main__":
    main()
