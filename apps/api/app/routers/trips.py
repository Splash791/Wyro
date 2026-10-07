import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.days import generate_days
from app.db import get_session
from app.models import Trip, TripCity, User
from app.schemas import DayRead, TripCreate, TripRead, UserRead

router = APIRouter()


def _to_trip_read(trip: Trip) -> TripRead:
    read = TripRead.model_validate(trip)
    read.days = [DayRead(**vars(d)) for d in generate_days(trip.cities)]
    return read


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/trips", response_model=list[TripRead])
def list_trips(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[TripRead]:
    trips = session.scalars(
        select(Trip).where(Trip.user_id == user.id).order_by(Trip.start_date)
    ).all()
    return [_to_trip_read(t) for t in trips]


@router.post("/trips", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip(
    body: TripCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TripRead:
    trip = Trip(
        user_id=user.id,
        title=body.title,
        start_date=body.start_date,
        end_date=body.end_date,
        cities=[TripCity(**c.model_dump()) for c in body.cities],
    )
    session.add(trip)
    session.flush()
    session.refresh(trip)
    return _to_trip_read(trip)


@router.get("/trips/{trip_id}", response_model=TripRead)
def get_trip(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TripRead:
    trip = session.get(Trip, trip_id)
    if trip is None or trip.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return _to_trip_read(trip)
