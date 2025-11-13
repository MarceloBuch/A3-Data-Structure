# providers.py
import os, requests
from typing import List, Dict, Any
from datetime import datetime, timedelta
from models import Flight

def _parse_iso(iso_str: str):
    """Aceita '2025-09-01T10:30:00Z' ou com offset '+00:00'."""
    if not iso_str:
        return None, None
    s = iso_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt.date().isoformat(), dt.strftime("%H:%M")
    except Exception:
        # se vier só 'YYYY-MM-DD'
        if len(iso_str) == 10:
            return iso_str, "00:00"
        return None, None

def _mk_flight(origin: str, destination: str, airline: str, departure_at: str,
               duration_min: int | None, price: float) -> Flight:
    d_date, d_time = _parse_iso(departure_at)
    if d_date is None:
        # fallback seguro
        d_date, d_time = "1970-01-01", "00:00"
    # chegada: se houver duração calculamos; senão, reaproveitamos partida
    if duration_min is not None:
        dt = datetime.fromisoformat(f"{d_date} {d_time}:00")
        at = dt + timedelta(minutes=int(duration_min))
        a_time = at.strftime("%H:%M")
    else:
        a_time = d_time
    return Flight(
        flight_id=f"API-{origin}-{destination}-{d_date}-{d_time}",
        airline=airline or "N/A",
        origin=origin,
        destination=destination,
        date=d_date,
        depart_time=d_time,
        arrive_time=a_time,
        price=float(price or 0.0),
    )

class TravelpayoutsClient:
    """
    Aviasales / Travelpayouts Data API
    Docs:
      - v3 search_by_price_range / prices_for_dates
      - v2 latest / month-matrix / nearest-places-matrix (cache ~48h)
    """
    BASE = "https://api.travelpayouts.com"

    def __init__(self, token: str | None = None, market: str = "br", currency: str = "BRL"):
        self.token = token or os.getenv("TRAVELPAYOUTS_TOKEN", "")
        self.market = market
        self.currency = currency
        if not self.token:
            raise RuntimeError(
                "Defina a variável de ambiente TRAVELPAYOUTS_TOKEN (grátis no painel Travelpayouts)."
            )

    def prices_for_dates(
        self,
        origin: str,
        destination: str,
        departure_at: str,       # "YYYY-MM-DD"
        direct: bool = False,
        limit: int = 50,
        sorting: str = "price"
    ) -> List[Flight]:
        # v3: devolve preços por datas específicas com airline + departure_at
        # Doc de referência e exemplos públicos. :contentReference[oaicite:2]{index=2}
        url = f"{self.BASE}/aviasales/v3/prices_for_dates"
        params = {
            "origin": origin,
            "destination": destination,
            "departure_at": departure_at,
            "direct": str(direct).lower(),
            "limit": limit,
            "sorting": sorting,
            "currency": self.currency,
            "market": self.market,
            "token": self.token,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        js = r.json()
        items = js.get("data") or js.get("tickets") or []
        flights: List[Flight] = []
        for it in items:
            price = it.get("price") or it.get("value")
            airline = it.get("airline") or it.get("main_airline")
            dep = it.get("departure_at") or it.get("depart_date")
            duration = it.get("duration")
            flights.append(_mk_flight(origin, destination, airline, dep, duration, price))
        return flights

    def latest(
        self,
        origin: str | None,
        destination: str | None,
        period_type: str = "month",
        beginning_of_period: str | None = None,
        one_way: bool = False,
        sorting: str = "price",
        limit: int = 100,
    ) -> List[Flight]:
        # v2/latest — preços encontrados recentemente (retorna depart_date e duration)
        # Doc pública com exemplo de resposta. :contentReference[oaicite:3]{index=3}
        url = f"{self.BASE}/v2/prices/latest"
        params = {
            "origin": origin or "",
            "destination": destination or "",
            "period_type": period_type,
            "beginning_of_period": beginning_of_period or "",
            "one_way": str(one_way).lower(),
            "sorting": sorting,
            "currency": self.currency,
            "market": self.market,
            "limit": limit,
            "page": 1,
            "token": self.token,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        js = r.json()
        flights: List[Flight] = []
        for it in js.get("data", []):
            price = it.get("value")
            dep_date = it.get("depart_date")  # YYYY-MM-DD
            # duration total em minutos, se houver
            duration = it.get("duration")
            flights.append(_mk_flight(
                it.get("origin", origin or "???"),
                it.get("destination", destination or "???"),
                airline=it.get("gate") or "N/A",
                departure_at=dep_date,   # sem hora → "00:00"
                duration_min=duration,
                price=price,
            ))
        return flights
