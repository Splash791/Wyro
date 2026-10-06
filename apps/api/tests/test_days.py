import datetime

from app.days import Day, generate_days
from app.models import TripCity


def _city(city, tz, arrive, leave, cc="JP"):
    return TripCity(
        city=city,
        country_code=cc,
        time_zone=tz,
        arrive_date=datetime.date.fromisoformat(arrive),
        leave_date=datetime.date.fromisoformat(leave),
    )


def test_single_day_city():
    cities = [_city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-01")]
    days = generate_days(cities)
    assert days == [
        Day(datetime.date(2026, 4, 1), "Tokyo", "JP", "Asia/Tokyo"),
    ]


def test_multi_day_city_inclusive():
    cities = [_city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-03")]
    days = generate_days(cities)
    assert [d.date for d in days] == [
        datetime.date(2026, 4, 1),
        datetime.date(2026, 4, 2),
        datetime.date(2026, 4, 3),
    ]


def test_month_boundary():
    cities = [_city("Tokyo", "Asia/Tokyo", "2026-01-30", "2026-02-01")]
    days = generate_days(cities)
    assert [d.date for d in days] == [
        datetime.date(2026, 1, 30),
        datetime.date(2026, 1, 31),
        datetime.date(2026, 2, 1),
    ]


def test_adjacent_cities_each_get_their_own_day():
    cities = [
        _city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-02"),
        _city("Kyoto", "Asia/Tokyo", "2026-04-02", "2026-04-03"),
    ]
    days = generate_days(cities)
    assert [(d.date.isoformat(), d.city) for d in days] == [
        ("2026-04-01", "Tokyo"),
        ("2026-04-02", "Tokyo"),
        ("2026-04-02", "Kyoto"),
        ("2026-04-03", "Kyoto"),
    ]


def test_cities_entered_out_of_order_are_sorted_by_arrival():
    cities = [
        _city("Kyoto", "Asia/Tokyo", "2026-04-05", "2026-04-06"),
        _city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-02"),
    ]
    days = generate_days(cities)
    assert [d.city for d in days] == ["Tokyo", "Tokyo", "Kyoto", "Kyoto"]
