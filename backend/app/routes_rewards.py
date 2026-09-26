"""Xaridor ballari, reyting, mukofotlar va haftalik missiyalar. Hammasi anonim qurilma ID bilan."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import get_db
from .services import ledger, rewards

router = APIRouter()


def _device(device_id: str | None) -> str:
    d = ledger.device_hash((device_id or "").strip())
    if not d or len(device_id or "") < 8:
        raise HTTPException(400, "device_id kerak (ilova avtomatik yaratadi)")
    return d


@router.get("/rewards/me")
def me(device_id: str = Query(...), db: Session = Depends(get_db)):
    return rewards.summary(db, _device(device_id))


class NicknameIn(BaseModel):
    device_id: str
    nickname: str = Field(max_length=40)


@router.post("/rewards/nickname")
def nickname(req: NicknameIn, db: Session = Depends(get_db)):
    try:
        return {"nickname": rewards.set_nickname(db, _device(req.device_id), req.nickname)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/rewards/leaderboard")
def leaderboard(device_id: str | None = None, days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    dev = ledger.device_hash(device_id) if device_id else ""
    return rewards.leaderboard(db, days=days, device=dev)


@router.get("/rewards/catalog")
def catalog():
    return {"items": rewards.CATALOG, "rules": [{"kind": k, "label": rewards.KIND_LABEL[k], "points": v}
                                                for k, v in rewards.POINTS.items()],
            "daily_cap": rewards.DAILY_CAP}


class RedeemIn(BaseModel):
    device_id: str
    reward_key: str


@router.post("/rewards/redeem")
def redeem(req: RedeemIn, db: Session = Depends(get_db)):
    try:
        return rewards.redeem(db, _device(req.device_id), req.reward_key)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/missions")
def missions(device_id: str | None = None, db: Session = Depends(get_db)):
    dev = ledger.device_hash(device_id) if device_id else ""
    return rewards.missions(db, device=dev)
