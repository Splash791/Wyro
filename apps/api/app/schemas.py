import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class TripCityCreate(BaseModel):
    city: str
    country_code: str
    time_zone: str
    arrive_date: datetime.date
    leave_date: datetime.date


class TripCreate(BaseModel):
    title: str
    start_date: datetime.date
    end_date: datetime.date
    cities: list[TripCityCreate]


class TripCityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    city: str
    country_code: str
    time_zone: str
    arrive_date: datetime.date
    leave_date: datetime.date


class DayRead(BaseModel):
    date: datetime.date
    city: str
    country_code: str
    time_zone: str


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    start_date: datetime.date
    end_date: datetime.date
    cities: list[TripCityRead]
    # default_factory=list only supports the validate-then-overwrite pattern in
    # routers.trips._to_trip_read, which always sets .days from generate_days();
    # an empty [] is never a legitimate terminal value.
    days: list[DayRead] = Field(default_factory=list)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    auth_provider: str
    import_address: str | None
