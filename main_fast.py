# main.py
import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from typing import List, Optional, Callable
from datetime import date, datetime

from models import Flight
import data_loader as dl              # parse_csv / write_csv / generate_synthetic / AIRLINES / AIRPORTS
from algorithms import sort_list, search_by_value
from providers import TravelpayoutsClient

APP_TITLE = "Flight Finder — CustomTkinter + Treeview + Travelpayouts (dark + busca flexível)"

# ---------------- Config (config.json ao lado do script) ----------------
CONFIG_PATH = Path(__file__).resolve().with_name("config.json")

def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Dialog de configuração do token ----------------
class TPConfigDialog(ctk.CTkToplevel):
    def __init__(self, master, initial_token: str | None):
        super().__init__(master)
        self.title("Configurar Travelpayouts")
        self.geometry("520x240")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        info = ("Cole seu token do Travelpayouts (grátis no painel). "
                "Ele será salvo localmente em config.json.")
        ctk.CTkLabel(self, text=info, wraplength=480, justify="left").pack(fill="x", padx=12, pady=(12,8))

        row = ctk.CTkFrame(self); row.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(row, text="Token:").pack(side="left", padx=(0,8))
        self.ent = ctk.CTkEntry(row, width=360, show="•")
        if initial_token:
            self.ent.insert(0, initial_token)
        self.ent.pack(side="left", padx=(0,8))

        self.show_var = tk.BooleanVar(value=False)
        def toggle_show():
            self.ent.configure(show="" if self.show_var.get() else "•")
        ctk.CTkCheckBox(row, text="Mostrar", variable=self.show_var, command=toggle_show).pack(side="left")

        btns = ctk.CTkFrame(self); btns.pack(fill="x", padx=12, pady=(4,12))
        ctk.CTkButton(btns, text="Testar conexão", command=self._test).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Salvar", command=self._save).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Cancelar", fg_color="gray", command=self._cancel).pack(side="right", padx=4)

        self.status = ctk.CTkLabel(self, text="")
        self.status.pack(fill="x", padx=12, pady=(0,8))

    def _test(self):
        token = self.ent.get().strip()
        if not token:
            messagebox.showerror("Token vazio", "Informe um token antes de testar.")
            return
        self.status.configure(text="Testando…")
        self.update_idletasks()
        try:
            month_start = date.today().replace(day=1).isoformat()
            cli = TravelpayoutsClient(token=token)
            _ = cli.latest("GRU", "SDU", period_type="month", beginning_of_period=month_start, limit=1)
            self.status.configure(text="✅ Conexão OK!")
        except Exception as e:
            self.status.configure(text=f"❌ Falhou: {e}")

    def _save(self):
        token = self.ent.get().strip()
        if not token:
            if not messagebox.askyesno("Salvar sem token?", "O token está vazio. Deseja salvar assim mesmo?"):
                return
        self.result = token
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

# ---------------- App ----------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.title(APP_TITLE)
        self.geometry("1200x740")
        self.minsize(1040, 640)

        self.cfg = load_config()
        self.all_flights: List[Flight] = []
        self.filtered: List[Flight] = []
        self.sorted_by_key: Optional[str] = None

        self._build_ui()

    # ---------- TEMA DARK para ttk.Treeview ----------
    def _style_dark_treeview(self):
        """Aplica tema dark ao ttk.Treeview e cabeçalhos."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        BG = "#191919"       # fundo da tabela
        FG = "#EAEAEA"       # texto normal
        HDR_BG = "#222222"   # fundo do header
        HDR_FG = "#EDEDED"   # texto do header
        GRID = "#2B2B2B"     # linhas/bordas
        SEL_BG = "#2F6B9A"   # seleção
        SEL_FG = "#FFFFFF"   # texto em seleção

        style.configure(
            "Dark.Treeview",
            background=BG,
            fieldbackground=BG,
            foreground=FG,
            bordercolor=GRID,
            borderwidth=0,
            rowheight=28,
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", SEL_BG)],
            foreground=[("selected", SEL_FG)],
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=HDR_BG,
            foreground=HDR_FG,
            relief="flat",
            bordercolor=GRID,
            borderwidth=0,
        )
        style.map(
            "Dark.Treeview.Heading",
            background=[("active", HDR_BG)],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

    # ---------------- UI ----------------
    def _build_ui(self):
        self._style_dark_treeview()   # aplica tema dark da tabela

        # Topbar
        top = ctk.CTkFrame(self); top.pack(fill="x", padx=10, pady=(10,6))
        ctk.CTkButton(top, text="Carregar CSV…", command=self.load_csv).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Gerar Dataset Demo", command=self.generate_demo).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Salvar resultados CSV…", command=self.save_results).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Limpar filtros", command=self.clear_filters).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Configurar Travelpayouts…", command=self.config_tp).pack(side="right", padx=4)

        # Filtros / Opções
        box = ctk.CTkFrame(self); box.pack(fill="x", padx=10, pady=6)

        self.origin = tk.StringVar()
        self.destination = tk.StringVar()
        self.date = tk.StringVar()
        self.max_price = tk.StringVar()
        self.airline = tk.StringVar()

        self.sort_key = tk.StringVar(value="price")
        self.sort_algo = tk.StringVar(value="timsort")
        self.sort_desc = tk.BooleanVar(value=False)

        self.search_algo = tk.StringVar(value="linear")
        self.search_mode = tk.StringVar(value="<=")
        self.search_value = tk.StringVar()

        # Linha 1
        r1 = ctk.CTkFrame(box); r1.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(r1, text="Origem").pack(side="left")
        self.cb_origin = ctk.CTkComboBox(r1, variable=self.origin, width=90, values=sorted(dl.AIRPORTS))
        self.cb_origin.pack(side="left", padx=(4,10))
        ctk.CTkLabel(r1, text="Destino").pack(side="left")
        self.cb_dest = ctk.CTkComboBox(r1, variable=self.destination, width=90, values=sorted(dl.AIRPORTS))
        self.cb_dest.pack(side="left", padx=(4,10))
        ctk.CTkLabel(r1, text="Data (YYYY[-MM[-DD]])").pack(side="left")
        ctk.CTkEntry(r1, textvariable=self.date, width=150).pack(side="left", padx=(4,10))
        ctk.CTkLabel(r1, text="Máx. preço").pack(side="left")
        ctk.CTkEntry(r1, textvariable=self.max_price, width=110).pack(side="left", padx=(4,10))
        ctk.CTkLabel(r1, text="Companhia").pack(side="left")
        self.cb_airline = ctk.CTkComboBox(r1, variable=self.airline, width=150, values=sorted(dl.AIRLINES))
        self.cb_airline.pack(side="left", padx=(4,10))

        # Linha 2
        r2 = ctk.CTkFrame(box); r2.pack(fill="x", padx=8, pady=(0,8))
        ctk.CTkLabel(r2, text="Ordenar por").pack(side="left")
        ctk.CTkComboBox(r2, variable=self.sort_key, width=140, values=["price","depart_time","duration"]).pack(side="left", padx=(4,10))
        ctk.CTkLabel(r2, text="Algoritmo").pack(side="left")
        ctk.CTkComboBox(r2, variable=self.sort_algo, width=150, values=["timsort","mergesort","quicksort","insertion","selection","bubble"]).pack(side="left", padx=(4,10))
        ctk.CTkCheckBox(r2, text="Decrescente", variable=self.sort_desc).pack(side="left")

        ctk.CTkLabel(r2, text="Busca por preço").pack(side="left", padx=(20,6))
        ctk.CTkComboBox(r2, variable=self.search_algo, width=90, values=["linear","binary"]).pack(side="left")
        ctk.CTkComboBox(r2, variable=self.search_mode, width=70, values=["==","<=",">="]).pack(side="left", padx=6)
        ctk.CTkEntry(r2, textvariable=self.search_value, width=120).pack(side="left")

        ctk.CTkButton(r2, text="Aplicar Filtros + Ordenar", command=self.apply_filters_and_sort).pack(side="left", padx=12)
        ctk.CTkButton(r2, text="Executar Busca por Preço", command=self.run_search_price).pack(side="left", padx=4)

        # ONLINE (Travelpayouts) — campos OPCIONAIS
        online = ctk.CTkFrame(self); online.pack(fill="x", padx=10, pady=(0,8))
        self.online_date = tk.StringVar()
        ctk.CTkLabel(
            online, 
            text="ONLINE · Origem (opcional) / Destino (opcional) / Data (opcional: YYYY-MM ou YYYY-MM-DD)"
        ).pack(side="left", padx=(0,8))
        self.ent_o = ctk.CTkEntry(online, width=80); self.ent_o.insert(0, ""); self.ent_o.pack(side="left", padx=4)
        self.ent_d = ctk.CTkEntry(online, width=80); self.ent_d.insert(0, ""); self.ent_d.pack(side="left", padx=4)
        self.ent_date = ctk.CTkEntry(online, textvariable=self.online_date, width=140); 
        self.ent_date.insert(0, ""); self.ent_date.pack(side="left", padx=4)
        ctk.CTkButton(online, text="Buscar Online (Travelpayouts)", command=self.fetch_online).pack(side="left", padx=12)

        # Tabela (rápida) — ttk.Treeview dark dentro do CTk
        table_f = ctk.CTkFrame(self); table_f.pack(fill="both", expand=True, padx=10, pady=(0,8))
        cols = ("flight_id","airline","origin","destination","date","depart","arrive","dur","price")
        self.tree = ttk.Treeview(table_f, columns=cols, show="headings", height=20, style="Dark.Treeview")
        headings = ["ID","Companhia","Origem","Destino","Data","Partida","Chegada","Duração (min)","Preço"]
        for c, h in zip(cols, headings):
            self.tree.heading(c, text=h, anchor="center")
            self.tree.column(c, anchor="center", width=100)
        self.tree.column("airline", width=140)
        self.tree.column("dur", width=120)
        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar dark (CustomTkinter)
        vs = ctk.CTkScrollbar(table_f, command=self.tree.yview)
        vs.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vs.set)

        # Linhas zebradas
        self.tree.tag_configure("odd",  background="#1E1E1E")
        self.tree.tag_configure("even", background="#171717")

        # Rodapé
        token_status = "OK" if self.cfg.get("travelpayouts_token") else "—"
        self.metrics_lbl = ctk.CTkLabel(self, text=f"Pronto. Token: {token_status}")
        self.metrics_lbl.pack(fill="x", padx=10, pady=(0,6))
        self.status_lbl = ctk.CTkLabel(self, text="Dica: gere dataset demo ou use a busca online (configure o token primeiro).")
        self.status_lbl.pack(fill="x", padx=10, pady=(0,10))

    # ---------------- Ações Topbar ----------------
    def config_tp(self):
        dlg = TPConfigDialog(self, initial_token=self.cfg.get("travelpayouts_token"))
        self.wait_window(dlg)
        if dlg.result is not None:
            self.cfg["travelpayouts_token"] = dlg.result
            save_config(self.cfg)
            token_status = "OK" if dlg.result else "—"
            self.metrics_lbl.configure(text=f"Configuração salva. Token: {token_status}")

    def load_csv(self):
        path = filedialog.askopenfilename(title="Escolha o CSV", filetypes=[("CSV","*.csv")])
        if not path:
            return
        try:
            flights = dl.parse_csv(path)
        except Exception as e:
            messagebox.showerror("Erro ao ler CSV", str(e))
            return
        self.set_dataset(flights, f"Carregado {len(flights)} voos de '{path}'")

    def generate_demo(self):
        flights = dl.generate_synthetic(n=1200, days=20)
        self.set_dataset(flights, f"Dataset demo gerado com {len(flights)} voos.")

    def save_results(self):
        if not self.filtered:
            messagebox.showinfo("Nada a salvar", "Não há resultados na tabela.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not path:
            return
        try:
            dl.write_csv(path, self.filtered)
            messagebox.showinfo("OK", f"Resultados salvos em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

    def clear_filters(self):
        self.origin.set(""); self.destination.set(""); self.date.set("")
        self.max_price.set(""); self.airline.set(""); self.search_value.set("")
        self.sort_key.set("price"); self.sort_algo.set("timsort"); self.sort_desc.set(False)
        self.search_algo.set("linear"); self.search_mode.set("<=")
        self.filtered = self.all_flights
        self.refresh_table(self.filtered)
        self.metrics_lbl.configure(text="Filtros limpos.")

    # ---------------- Dataset / Tabela ----------------
    def set_dataset(self, flights: List[Flight], msg: str):
        self.all_flights = flights
        self.filtered = flights
        self.sorted_by_key = None
        uniq_airports = sorted({f.origin for f in flights} | {f.destination for f in flights}) or dl.AIRPORTS
        uniq_airlines = sorted({f.airline for f in flights}) or dl.AIRLINES
        self.cb_origin.configure(values=uniq_airports)
        self.cb_dest.configure(values=uniq_airports)
        self.cb_airline.configure(values=uniq_airlines)
        self.refresh_table(self.filtered)
        self.status_lbl.configure(text=msg)

    def refresh_table(self, flights: List[Flight]):
        self.tree.delete(*self.tree.get_children())
        to_show = flights[:5000]
        for i in range(0, len(to_show), 500):
            chunk = to_show[i:i+500]
            for idx, f in enumerate(chunk, start=i):
                tag = "odd" if (idx % 2) else "even"
                self.tree.insert(
                    "", "end",
                    values=(f.flight_id, f.airline, f.origin, f.destination, f.date,
                            f.depart_time, f.arrive_time, f.duration_minutes, f"{f.price:.2f}"),
                    tags=(tag,),
                )
            self.update_idletasks()

    # ---------------- Filtros, Ordenação e Busca ----------------
    def _apply_filters(self, data: List[Flight]) -> List[Flight]:
        def ok(f: Flight) -> bool:
            if self.origin.get() and f.origin != self.origin.get(): return False
            if self.destination.get() and f.destination != self.destination.get(): return False
            if self.airline.get() and f.airline != self.airline.get(): return False
            if self.date.get().strip():
                d = self.date.get().strip()
                if len(d) == 10:
                    if f.date != d: return False
                elif len(d) == 7:
                    if not f.date.startswith(d): return False
                elif len(d) == 4:
                    if not f.date.startswith(d): return False
                else:
                    return False
            if self.max_price.get().strip():
                try: m = float(self.max_price.get().replace(",", "."))
                except ValueError: return False
                if f.price > m: return False
            return True
        return [f for f in data if ok(f)]

    def _sort_key(self) -> Callable[[Flight], object]:
        k = self.sort_key.get()
        if k == "price": return lambda f: f.price
        if k == "depart_time": return lambda f: (f.date, f.depart_time)
        if k == "duration": return lambda f: f.duration_minutes
        return lambda f: f.price

    def apply_filters_and_sort(self):
        if not self.all_flights:
            messagebox.showwarning("Sem dados", "Carregue um CSV ou gere um dataset.")
            return
        data = self._apply_filters(self.all_flights)
        try:
            sorted_data, sm = sort_list(self.sort_algo.get(), data, self._sort_key(), reverse=self.sort_desc.get())
        except Exception as e:
            messagebox.showerror("Erro de ordenação", str(e))
            return
        
        print("\n--- MÉTRICAS DE ORDENAÇÃO ---")
        print(sm) 
        print("---------------------------\n")

        self.filtered = sorted_data
        self.sorted_by_key = self.sort_key.get()
        self.refresh_table(self.filtered)
        comps = "-" if sm.comparisons is None else f"{sm.comparisons:,}"
        moves = "-" if sm.swaps_or_moves is None else f"{sm.swaps_or_moves:,}"
        self.metrics_lbl.configure(text=(
            f"Ordenados {sm.n} por '{self.sort_key.get()}' ({sm.algorithm}) em {sm.time_ms:.2f} ms | "
            f"comparações={comps}, movs={moves}. Resultados: {len(self.filtered)}"
        ))

    def run_search_price(self):
        if not self.filtered:
            messagebox.showwarning("Sem resultados", "Não há resultados na tabela para buscar.")
            return
        try:
            target = float(self.search_value.get().replace(",", "."))
        except Exception:
            messagebox.showerror("Entrada inválida", "Informe um preço numérico.")
            return
        data = list(self.filtered)
        assume_sorted = False
        if self.search_algo.get() == "binary":
            if self.sorted_by_key == "price" and not self.sort_desc.get():
                assume_sorted = True
            else:
                data, _ = sort_list("timsort", data, key=lambda f: f.price, reverse=False)
                assume_sorted = True
        res, met = search_by_value(self.search_algo.get(), data, key=lambda f: f.price,
                                   target=target, mode=self.search_mode.get(), assume_sorted=assume_sorted)
        
        print("\n--- MÉTRICAS DE BUSCA ---")
        print(met)
        print("-----------------------\n")

        if not res:
            self.metrics_lbl.configure(text=f"Busca ({met.algorithm}, {met.details}) {met.time_ms:.2f} ms — 0 itens.")
            messagebox.showinfo("Sem resultados", "Nada encontrado para o critério.")
            return
        self.refresh_table(res)
        self.metrics_lbl.configure(text=(
            f"Busca ({met.algorithm}, {met.details}) {met.time_ms:.2f} ms | "
            f"comparações={met.comparisons} | encontrados={len(res)}"
        ))

    # ---------------- Helpers ONLINE ----------------
    @staticmethod
    def _month_start_from_input(s: str | None) -> str:
        """Converte '', 'YYYY-MM' ou 'YYYY-MM-DD' para 'YYYY-MM-01'. Se vazio, mês atual."""
        if not s or not s.strip():
            return date.today().replace(day=1).isoformat()
        s = s.strip()
        try:
            if len(s) == 7:   # YYYY-MM
                dt = datetime.strptime(s, "%Y-%m")
                return dt.replace(day=1).date().isoformat()
            elif len(s) == 10:  # YYYY-MM-DD
                dt = datetime.strptime(s, "%Y-%m-%d")
                return dt.replace(day=1).date().isoformat()
            else:
                return date.today().replace(day=1).isoformat()
        except Exception:
            return date.today().replace(day=1).isoformat()

    # ---------------- ONLINE (Travelpayouts) ----------------
    def fetch_online(self):
        origin = self.ent_o.get().strip().upper() or None
        dest = self.ent_d.get().strip().upper() or None
        date_str = self.ent_date.get().strip() or None
        token = self.cfg.get("travelpayouts_token", "")

        if not token:
            messagebox.showerror("Token ausente", "Configure o token do Travelpayouts antes (menu superior).")
            return

        # Se o usuário forneceu os 3 (origem+destino+data YYYY-MM-DD) => tentamos a busca exata
        use_exact = bool(origin and dest and date_str and len(date_str) == 10)
        month_start = self._month_start_from_input(date_str)

        def work():
            try:
                cli = TravelpayoutsClient(token=token)
                flights: List[Flight] = []

                if use_exact:
                    flights = cli.prices_for_dates(origin, dest, date_str, direct=False, limit=120)
                    if not flights:
                        flights = cli.latest(origin, dest, period_type="month", beginning_of_period=month_start, limit=200)
                else:
                    flights = cli.latest(origin, dest, period_type="month", beginning_of_period=month_start, limit=200)

                if not flights:
                    raise RuntimeError("Nenhum resultado retornado. Tente informar ao menos origem OU destino, ou outra data.")

                parts = []
                parts.append(origin or "*")
                parts.append(dest or "*")
                tag = " · ".join(parts) + f" · {month_start[:7]}"
                self.set_dataset(flights, f"Online: {len(flights)} ofertas [{tag}] (Travelpayouts).")
            except Exception as e:
                self.status_lbl.configure(text=f"Falha no online: {e}")

        threading.Thread(target=work, daemon=True).start()

if __name__ == "__main__":
    App().mainloop()
