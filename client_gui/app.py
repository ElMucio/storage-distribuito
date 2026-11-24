# GUI desktop creata con Tkinter.
# Le chiamate http girano in thread separato, cosi da non freezzare la finestra

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api import ApiClient, ApiError


DEFAULT_SERVER = "http://localhost:8000"


class LoginScreen(ttk.Frame):
    # Schermata di login + registrazione. Bisogna registrarsi prima!
    def __init__(self, app):
        super().__init__(app, padding=24)
        self.app = app

        ttk.Label(self, text="Storage Distribuito",
                  font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 18))

        ttk.Label(self, text="Server:").grid(row=1, column=0, sticky="w", pady=4)
        self.server_var = tk.StringVar(value=DEFAULT_SERVER)
        ttk.Entry(self, textvariable=self.server_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(self, text="Username:").grid(row=2, column=0, sticky="w", pady=4)
        self.user_var = tk.StringVar()
        self.user_entry = ttk.Entry(self, textvariable=self.user_var)
        self.user_entry.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(self, text="Password:").grid(row=3, column=0, sticky="w", pady=4)
        self.pw_var = tk.StringVar()
        self.pw_entry = ttk.Entry(self, textvariable=self.pw_var, show="*")
        self.pw_entry.grid(row=3, column=1, sticky="ew", pady=4)

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, pady=(18, 8))
        self.login_btn = ttk.Button(btns, text="Login", command=self._login_click, width=14)
        self.login_btn.pack(side="left", padx=8)
        self.register_btn = ttk.Button(btns, text="Registrati", command=self._register_click, width=14)
        self.register_btn.pack(side="left", padx=8)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, foreground="#555").grid(
            row=5, column=0, columnspan=2, pady=4)

        self.columnconfigure(1, weight=1)
        self.pw_entry.bind("<Return>", lambda e: self._login_click())
        self.user_entry.focus()

    def _imposta_occupato(self, occupato, messaggio=""):
        # Abilita/disabilita i bottoni e aggiorna la status bar.
        # Si usa durante le chiamate HTTP. Evitiamo conflitti che si creerebbero in
        # in caso di doppio click
        stato = "disabled" if occupato else "normal"
        self.login_btn.config(state=stato)
        self.register_btn.config(state=stato)
        self.status_var.set(messaggio)

    def _leggi_modulo(self):
        # Legge e valida i tre campi del form. Restituisce None se incompleti.
        s = self.server_var.get().strip()
        u = self.user_var.get().strip()
        p = self.pw_var.get()
        if not s or not u or not p:
            messagebox.showwarning("Dati mancanti", "Compila server, username e password.")
            return None
        return s, u, p

    def _login_click(self):
       
        vals = self._leggi_modulo()
        if not vals:
            return
        s, u, p = vals
        self.app.client = ApiClient(s)
        self._imposta_occupato(True, "Login in corso...")
        threading.Thread(target=self._login_work, args=(u, p), daemon=True).start()

    def _login_work(self, u, p):
        # Eseguito nel thread di lavoro: la GUI NON deve essere toccata da qui.
        err = None
        try:
            self.app.client.login(u, p)
        except ApiError as e:
            err = e
        # Torno al main thread con after(0, ...) per aggiornare l'UI.
        self.after(0, lambda: self._login_done(err))

    def _login_done(self, err):
        # Eseguito nel main thread: posso aggiornare i widget Tk.
        self._imposta_occupato(False, "")
        if err is None:
            self.app.show_files()
        else:
            messagebox.showerror("Login fallito", err.detail)

    def _register_click(self):
        
        vals = self._leggi_modulo()
        if not vals:
            return
        s, u, p = vals
        self.app.client = ApiClient(s)
        self._imposta_occupato(True, "Registrazione in corso...")
        threading.Thread(target=self._register_work, args=(u, p), daemon=True).start()

    def _register_work(self, u, p):

        err = None
        try:
            self.app.client.register(u, p)
        except ApiError as e:
            err = e
        self.after(0, lambda: self._register_done(err))

    def _register_done(self, err):

        self._imposta_occupato(False, "")
        if err is None:
            messagebox.showinfo("Registrazione OK", "Utente creato. Ora puoi fare login.")
        else:
            messagebox.showerror("Registrazione fallita", err.detail)


class FilesScreen(ttk.Frame):

    # Schermata con lista file dell'utente e con i bottoni di azione.
    # Doppio click su un file = download. 
    # Viene richiesta una conferma esplicita per la delete.
    def __init__(self, app):
        super().__init__(app, padding=16)
        self.app = app

        ttk.Label(self, text="File del tuo storage",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, pady=(12, 8))
        self.files_list = tk.Listbox(list_frame, activestyle="dotbox", height=10)
        self.files_list.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.files_list.yview)
        scroll.pack(side="right", fill="y")
        self.files_list.config(yscrollcommand=scroll.set)
        self.files_list.bind("<Double-Button-1>", lambda e: self._download_click())

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=4)
        self.refresh_btn = ttk.Button(actions, text="Aggiorna", command=self._refresh, width=12)
        self.refresh_btn.pack(side="left", padx=4)
        self.upload_btn = ttk.Button(actions, text="Upload", command=self._upload_click, width=12)
        self.upload_btn.pack(side="left", padx=4)
        self.download_btn = ttk.Button(actions, text="Download", command=self._download_click, width=12)
        self.download_btn.pack(side="left", padx=4)
        self.delete_btn = ttk.Button(actions, text="Elimina", command=self._delete_click, width=12)
        self.delete_btn.pack(side="left", padx=4)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=(8, 0))
        self.logout_btn = ttk.Button(bottom, text="Logout", command=self.app.logout, width=12)
        self.logout_btn.pack(side="right")

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, foreground="#555").pack(fill="x", pady=(8, 0))

        self._refresh()

    def _tutti_i_bottoni(self):
        return [self.refresh_btn, self.upload_btn, self.download_btn,
                self.delete_btn, self.logout_btn]

    def _imposta_occupato(self, occupato, messaggio=""):
        # Disabilita TUTTI i bottoni, incluso Logout
        stato = "disabled" if occupato else "normal"
        for b in self._tutti_i_bottoni():
            b.config(state=stato)
        self.status_var.set(messaggio)

    def _file_selezionato(self):
        # Restituisce il nome del file evidenziato nella Listbox, o None.
        sel = self.files_list.curselection()
        if not sel:
            messagebox.showwarning("Nessuna selezione", "Seleziona un file dalla lista.")
            return None
        return self.files_list.get(sel[0])

    def _refresh(self):
        # Ricarica la lista file dal broker.
        self._imposta_occupato(True, "Aggiorno la lista...")
        threading.Thread(target=self._refresh_work, daemon=True).start()

    def _refresh_work(self):
        err = None
        files = None
        try:
            files = self.app.client.list_files()
        except ApiError as e:
            err = e
        self.after(0, lambda: self._refresh_done(files, err))

    def _refresh_done(self, files, err):
        self._imposta_occupato(False, "")
        if err:
            messagebox.showerror("Errore", err.detail)
            return
        self.files_list.delete(0, tk.END)
        for f in sorted(files):
            self.files_list.insert(tk.END, f)
        self.status_var.set(f"{len(files)} file presenti.")

    def _upload_click(self):
        # Apre un file dialog, legge il file in RAM e lancia l'upload in thread.
        path = filedialog.askopenfilename(title="Scegli un file da caricare")
        if not path:
            return
        name = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror("Errore", f"Impossibile leggere il file: {e}")
            return
        self._imposta_occupato(True, f"Upload di {name} ({len(content)/1024:.0f} KB)...")
        threading.Thread(target=self._upload_work, args=(name, content), daemon=True).start()

    def _upload_work(self, name, content):
        err = None
        try:
            self.app.client.upload(name, content)
        except ApiError as e:
            err = e
        self.after(0, lambda: self._upload_done(name, err))

    def _upload_done(self, name, err):
        if err:
            self._imposta_occupato(False, "")
            messagebox.showerror("Upload fallito", err.detail)
            return
        self.status_var.set(f"Upload di {name} completato.")
        # RicaRefresho la lista dopo una mutazione.
        self._refresh()

    def _download_click(self):
        # Apre un file dialog per scegliere dove salvare; poi scarica in thread.
        name = self._file_selezionato()
        if not name:
            return
        path = filedialog.asksaveasfilename(title="Salva con nome", initialfile=name)
        if not path:
            return
        self._imposta_occupato(True, f"Download di {name}...")
        threading.Thread(target=self._download_work, args=(name, path), daemon=True).start()

    def _download_work(self, name, path):
        # Errori di disco e di rete
        # entrambi tradotti in ApiError,
        # cosi' il main thread ha un solo ramo "if err:".
        err = None
        saved = None
        try:
            data = self.app.client.download(name)
            with open(path, "wb") as f:
                f.write(data)
            saved = path
        except ApiError as e:
            err = e
        except OSError as e:
            err = ApiError(0, f"Errore di scrittura su disco: {e}")
        self.after(0, lambda: self._download_done(saved, err))

    def _download_done(self, saved, err):
        self._imposta_occupato(False, "")
        if err:
            messagebox.showerror("Download fallito", err.detail)
            return
        messagebox.showinfo("Download OK", f"File salvato in:\n{saved}")
        self.status_var.set("Download completato.")

    def _delete_click(self):
        # Conferma esplicita per elminare
        name = self._file_selezionato()
        if not name:
            return
        if not messagebox.askyesno("Conferma", f"Eliminare definitivamente '{name}' ?"):
            return
        self._imposta_occupato(True, f"Elimino {name}...")
        threading.Thread(target=self._delete_work, args=(name,), daemon=True).start()

    def _delete_work(self, name):
        err = None
        try:
            self.app.client.delete(name)
        except ApiError as e:
            err = e
        self.after(0, lambda: self._delete_done(name, err))

    def _delete_done(self, name, err):
        if err:
            self._imposta_occupato(False, "")
            messagebox.showerror("Elimina fallita", err.detail)
            return
        self.status_var.set(f"{name} eliminato.")
        self._refresh()


class App(tk.Tk):
    # Finestra principale. Tiene lo stato di sessione (self.client = ApiClient)
    # e fa da "router" fra le due schermate.
    def __init__(self):
        super().__init__()
        self.title("Storage Distribuito")
        self.geometry("600x460")
        self.minsize(520, 380)
        try:
            self.tk.call("ttk::style", "theme", "use", "vista")
        except tk.TclError:
            pass

        self.client = ApiClient(DEFAULT_SERVER)
        self.current = None
        self.show_login()

    def _swap(self, new_frame):
        # Distruggo la schermata corrente e ci metto quella nuova.
        # Utiliziamo questo approccio per semplificare il reset dei dati dopo
        # il logout
        if self.current is not None:
            self.current.destroy()
        self.current = new_frame
        self.current.pack(fill="both", expand=True)

    def show_login(self):
        self._swap(LoginScreen(self))

    def show_files(self):
        self._swap(FilesScreen(self))

    def logout(self):
        self.client.logout()
        self.show_login()


def _windows_dpi_fix():
    # In windows esiste un bug noto, che in pc con frame alti
    # le schermate tkinter caricano sfuocate
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


if __name__ == "__main__":
    _windows_dpi_fix()
    App().mainloop()
