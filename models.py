from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Flight:
    flight_id: str
    airline: str
    origin: str
    destination: str
    date: str            # YYYY-MM-DD
    depart_time: str     # HH:MM (24h)
    arrive_time: str     # HH:MM (24h) - can cross midnight
    price: float         # in local currency

    @property
    def depart_datetime(self):
        return datetime.fromisoformat(f"{self.date} {self.depart_time}:00")

    @property
    def arrive_datetime(self):
        d = datetime.fromisoformat(f"{self.date} {self.arrive_time}:00")
        if d < self.depart_datetime:
            d += timedelta(days=1)
        return d

    @property
    def duration_minutes(self) -> int:
        return int((self.arrive_datetime - self.depart_datetime).total_seconds() // 60)

    def as_row(self):
        return [
            self.flight_id,
            self.airline,
            self.origin,
            self.destination,
            self.date,
            self.depart_time,
            self.arrive_time,
            f"{self.duration_minutes}",
            f"{self.price:.2f}",
        ]
