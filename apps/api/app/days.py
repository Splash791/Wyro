import datetime
from dataclasses import dataclass

from app.models import TripCity


@dataclass(frozen=True)
class Day:
    date: datetime.date
    city: str
    country_code: str
    time_zone: str


def generate_days(cities: list[TripCity]) -> list[Day]:
    days: list[Day] = []
    for city in sorted(cities, key=lambda c: c.arrive_date):
        current = city.arrive_date
        while current <= city.leave_date:
            days.append(Day(current, city.city, city.country_code, city.time_zone))
            current += datetime.timedelta(days=1)
    return days
