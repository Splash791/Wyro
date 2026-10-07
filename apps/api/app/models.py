import datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True)
    auth_provider: Mapped[str] = mapped_column(String)  # "google" | "apple" | "dev"
    import_address: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    start_date: Mapped[datetime.date] = mapped_column(Date)
    end_date: Mapped[datetime.date] = mapped_column(Date)
    offline_downloaded_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    cities: Mapped[list["TripCity"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripCity.arrive_date",
    )


class TripCity(Base):
    __tablename__ = "trip_cities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id"))
    city: Mapped[str] = mapped_column(String)
    country_code: Mapped[str] = mapped_column(String)  # ISO 3166-1 alpha-2
    time_zone: Mapped[str] = mapped_column(String)  # IANA, e.g. "Asia/Tokyo"
    arrive_date: Mapped[datetime.date] = mapped_column(Date)
    leave_date: Mapped[datetime.date] = mapped_column(Date)

    trip: Mapped["Trip"] = relationship(back_populates="cities")
