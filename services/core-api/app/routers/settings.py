"""Key/value settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.setting import Setting
from app.schemas.common import StatusResponse
from app.schemas.settings import SettingOut, SettingUpsert

router = APIRouter(prefix="/settings", tags=["settings"])


# --- Computer Use ---

@router.post("/computer-use/arm", response_model=StatusResponse)
def arm_computer_use(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    from app.services.computer_use import set_armed
    if set_armed(True):
        return StatusResponse(detail="armed")
    raise HTTPException(status_code=400, detail="Computer use disabled in config")

@router.post("/computer-use/disarm", response_model=StatusResponse)
def disarm_computer_use(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    from app.services.computer_use import set_armed
    set_armed(False)
    return StatusResponse(detail="disarmed")

@router.get("/computer-use/audit")
def get_computer_use_audit(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.computer_use import get_audit_log
    return get_audit_log()

# --- Key/Value Settings ---


@router.get("", response_model=list[SettingOut])
def list_settings(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SettingOut]:
    rows = db.execute(select(Setting)).scalars().all()
    return [SettingOut.model_validate(r) for r in rows]


@router.get("/{key}", response_model=SettingOut)
def get_setting(
    key: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingOut:
    row = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="setting not found")
    return SettingOut.model_validate(row)


@router.put("", response_model=SettingOut)
def upsert_setting(
    body: SettingUpsert,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingOut:
    row = db.execute(
        select(Setting).where(Setting.key == body.key)
    ).scalar_one_or_none()
    if row:
        row.value = body.value
    else:
        row = Setting(key=body.key, value=body.value)
        db.add(row)
    db.commit()
    db.refresh(row)
    return SettingOut.model_validate(row)


@router.delete("/{key}", response_model=StatusResponse)
def delete_setting(
    key: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    row = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="setting not found")
    db.delete(row)
    db.commit()
    return StatusResponse(detail="deleted")
