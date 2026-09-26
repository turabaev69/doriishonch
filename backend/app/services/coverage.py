from sqlalchemy import func

from ..config import settings
from ..models import Participant
from ..regions import UZ_CENTER

NAMANGAN_CENTER = {"lat": 40.9983, "lon": 71.6726, "zoom": 12}
NAMANGAN_NAMES = ("namangan", "namangan viloyati", "namangan shahri")


def in_scope(region: str) -> bool:
    return not settings.pharmacy_region or region.strip().lower() in NAMANGAN_NAMES


def pharmacies(query):
    if settings.pharmacy_region:
        query = query.filter(func.lower(func.trim(Participant.region)).in_(NAMANGAN_NAMES))
    return query


def center() -> dict:
    return NAMANGAN_CENTER if settings.pharmacy_region else UZ_CENTER
