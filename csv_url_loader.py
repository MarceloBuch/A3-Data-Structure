# csv_url_loader.py
import io, csv, requests
import customtkinter as ctk
from tkinter import messagebox
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Flight

def _norm_price(x) -> float:
    if x is None: return 0.0
    s = str(x).strip().replace("R$", "").replace("US$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and s.count(".") >= 1 else s
    try: return float(s)
    except: 
        try: return float(s.replace(",", "."))
        except: return 0.0

def _norm_time(x: Optional[str]) -> str:
    if not x: return "08:00"
    s = str(x).strip()
    # aceita "8", "8:3", "08:30", "0830"
    if s.isdigit() and len(s) in (3,4):
        s = s.zfill(4);  return f"{s[:2]}:{s[2:]}"
    if ":" in s:
        hh, mm = s.split(":")[:2]
        hh = hh.zfill(2); mm = mm.zfill(2)
        return f"{hh}:{mm}"
    if s.isdigit():
        return f"{int(s)%24:02d}:00"
    return "08:00"

def _norm_date(x: Optional[str]) -> str:
    if not x: return "1970-01-01"
    s = str(x).strip().replace("/", "-")
    # tenta YYYY-MM-DD, YYYY-MM, YYYY
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == "%Y-%m":   return dt.strftime("%Y-%m-01")
            if fmt == "%Y":      return dt.strftime("%Y-01-01")
            return dt.strftime("%Y-%m-%d")
        except: pass
    # tenta dd-mm-YYYY
    for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except: pass
    return "1970-01-01"

class CSVMappingDialog(ctk.CTkToplevel):
    """Dialog para o usuário mapear colunas do CSV para campos do Flight."""
    def __init__(self, master, headers: List[str]):
        super().__init__(master)
        self.title("Mapear colunas do CSV")
        self.geometry("520x420")
        self.resizable(False, False)
        self.grab_set()
        self.mapping = None

        fields = [
            ("flight_id",       "ID do voo (opcional)"),
            ("airline",         "Companhia (opcional)"),
            ("origin",          "Origem (IATA)"),
            ("destination",     "Destino (IATA)"),
            ("date",            "Data (YYYY-MM[-DD])"),
            ("depart_time",     "Partida (HH:MM) (opcional)"),
            ("arrive_time",     "Chegada (HH:MM) (opcional)"),
            ("duration_min",    "Duração (min) (opcional)"),
            ("price",           "Preço"),
        ]
        self.widgets = {}
        opts = ["— (vazio) —"] + headers
        body = ctk.CTkScrollableFrame(self); body.pack(fill="both", expand=True, padx=12, pady=12)
        for key, label in fields:
            row = ctk.CTkFrame(body); row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=label, width=220, anchor="w").pack(side="left")
            cb = ctk.CTkComboBox(row, values=opts, width=240)
            cb.set("— (vazio) —")
            cb.pack(side="left")
            self.widgets[key] = cb

        btns = ctk.CTkFrame(self); btns.pack(fill="x", padx=12, pady=(0,12))
        ctk.CTkButton(btns, text="OK", command=self._ok).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Cancelar", fg_color="gray", command=self._cancel).pack(side="right", padx=6)

    def _ok(self):
        self.mapping = {k: (w.get() if w.get() != "— (vazio) —" else None) for k, w in self.widgets.items()}
        # validações mínimas
        need = ["origin","destination","date","price"]
        miss = [f for f in need if not self.mapping.get(f)]
        if miss:
            messagebox.showerror("Campos obrigatórios", f"Faltam mapear: {', '.join(miss)}"); 
            return
        self.destroy()

    def _cancel(self):
        self.mapping = None
        self.destroy()

def _row_get(row: Dict[str, str], col: Optional[str]) -> Optional[str]:
    return None if not col else row.get(col)

def rows_to_flights(rows: List[Dict[str, str]], mapping: Dict[str, Optional[str]]) -> List[Flight]:
    flights: List[Flight] = []
    for i, r in enumerate(rows, 1):
        origin  = (_row_get(r, mapping.get("origin")) or "").strip().upper()
        dest    = (_row_get(r, mapping.get("destination")) or "").strip().upper()
        if not origin or not dest: 
            continue
        date    = _norm_date(_row_get(r, mapping.get("date")))
        dep     = _norm_time(_row_get(r, mapping.get("depart_time")))
        arr     = _norm_time(_row_get(r, mapping.get("arrive_time")))
        dur_s   = _row_get(r, mapping.get("duration_min"))
        try: duration = int(float(str(dur_s).replace(",", "."))) if dur_s else None
        except: duration = None
        # recalcula chegada se tiver duração
        if duration is not None:
            dt = datetime.fromisoformat(f"{date} {dep}:00") + timedelta(minutes=duration)
            arr = dt.strftime("%H:%M")
        airline = _row_get(r, mapping.get("airline")) or "N/A"
        price   = _norm_price(_row_get(r, mapping.get("price")))
        fid     = (_row_get(r, mapping.get("flight_id")) or f"CSV-{i}")

        flights.append(Flight(
            flight_id=fid,
            airline=str(airline),
            origin=origin,
            destination=dest,
            date=date,
            depart_time=dep,
            arrive_time=arr,
            price=price,
        ))
    return flights

def load_flights_from_url_via_mapping(master, url: str) -> List[Flight]:
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Informe uma URL iniciando com http(s)://")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    content = resp.content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise RuntimeError("CSV sem cabeçalho.")
    headers = [h.strip() for h in reader.fieldnames]
    rows = [dict(row) for row in reader]

    dlg = CSVMappingDialog(master, headers)
    master.wait_window(dlg)
    if dlg.mapping is None:
        return []
    return rows_to_flights(rows, dlg.mapping)
