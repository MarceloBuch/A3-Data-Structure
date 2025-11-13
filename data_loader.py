from typing import List, Iterable
from models import Flight
import csv
import random
from datetime import datetime, timedelta

AIRLINES = [
    "Azul", "Gol", "LATAM", "Voepass", "Sky", "Copa", "United", "Iberia", "TAP", "Air France"
]
AIRPORTS = [
    "GRU", "CGH", "VCP", "SDU", "GIG", "BSB", "CNF", "POA", "REC", "SSA",
    "FOR", "NAT", "CWB", "FLN", "BEL", "MCO", "JFK", "LIS", "CDG"
]

def parse_csv(path: str) -> List[Flight]:
    flights: List[Flight] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"flight_id","airline","origin","destination","date","depart_time","arrive_time","price"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"CSV must have headers: {sorted(required)}")
        for row in reader:
            flights.append(Flight(
                flight_id=row["flight_id"],
                airline=row["airline"],
                origin=row["origin"],
                destination=row["destination"],
                date=row["date"],
                depart_time=row["depart_time"],
                arrive_time=row["arrive_time"],
                price=float(row["price"].replace(",", ".")) if isinstance(row["price"], str) else float(row["price"]),
            ))
    return flights

def write_csv(path: str, flights: Iterable[Flight]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["flight_id","airline","origin","destination","date","depart_time","arrive_time","duration_min","price"])
        for fl in flights:
            w.writerow(fl.as_row())

def generate_synthetic(n: int = 400, start_date: str = None, days: int = 15, seed: int = 42) -> List[Flight]:
    random.seed(seed)
    flights: List[Flight] = []
    if start_date is None:
        start = datetime.today().date()
    else:
        start = datetime.fromisoformat(start_date).date()
    id_counter = 1
    for d in range(days):
        date = (start + timedelta(days=d)).isoformat()
        for _ in range(n // days):
            origin = random.choice(AIRPORTS)
            dest = random.choice([a for a in AIRPORTS if a != origin])
            airline = random.choice(AIRLINES)
            dep_hour = random.randint(5, 22)
            dep_min = random.choice([0,10,20,30,40,50])
            duration_min = random.randint(50, 720)  # 50 min to 12 hours
            arr_hour = (dep_hour + (dep_min + duration_min)//60) % 24
            arr_min = (dep_min + duration_min) % 60
            base_price = 120 + (duration_min/60)*80 + random.randint(-50, 350)
            if {origin,dest} & {"CDG","JFK","LIS","MCO"}:
                base_price += 400
            price = round(max(150, base_price), 2)
            flight_id = f"FF{id_counter:05d}"
            id_counter += 1
            flights.append(Flight(
                flight_id=flight_id,
                airline=airline,
                origin=origin,
                destination=dest,
                date=date,
                depart_time=f"{dep_hour:02d}:{dep_min:02d}",
                arrive_time=f"{arr_hour:02d}:{arr_min:02d}",
                price=price
            ))
    return flights
