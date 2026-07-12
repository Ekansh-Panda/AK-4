"""Key/value settings + computer-use configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings as app_settings
from app.db.session import get_db
from app.models.setting import Setting
from app.schemas.common import StatusResponse
from app.schemas.settings import ComputerUseSettings, SettingOut, SettingUpsert

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


@router.get("/computer-use", response_model=ComputerUseSettings)
def get_computer_use_settings(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComputerUseSettings:
    from app.services.settings_service import SettingsService

    svc = SettingsService(db)
    trust_level = svc.get("computer_use_trust_level") or app_settings.COMPUTER_USE_TRUST_LEVEL
    max_steps = int(svc.get("computer_use_max_steps") or app_settings.COMPUTER_USE_MAX_STEPS)
    plan_timeout_s = int(svc.get("computer_use_plan_timeout_s") or app_settings.COMPUTER_USE_PLAN_TIMEOUT_S)
    vision_enabled = str(svc.get("computer_use_vision_enabled") or app_settings.COMPUTER_USE_VISION_ENABLED).lower() in ("1", "true", "yes")
    audio_enabled = str(svc.get("computer_use_audio_enabled") or app_settings.COMPUTER_USE_AUDIO_ENABLED).lower() in ("1", "true", "yes")
    double_verify = str(svc.get("computer_use_double_verify") or app_settings.COMPUTER_USE_DOUBLE_VERIFY).lower() in ("1", "true", "yes")
    browser_enabled = str(svc.get("computer_use_browser_enabled") or app_settings.COMPUTER_USE_BROWSER_ENABLED).lower() in ("1", "true", "yes")

    return ComputerUseSettings(
        trust_level=trust_level,
        max_steps=max_steps,
        plan_timeout_s=plan_timeout_s,
        vision_enabled=vision_enabled,
        audio_enabled=audio_enabled,
        double_verify=double_verify,
        browser_enabled=browser_enabled,
    )


@router.put("/computer-use", response_model=ComputerUseSettings)
def put_computer_use_settings(
    body: ComputerUseSettings,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComputerUseSettings:
    from app.services.settings_service import SettingsService

    svc = SettingsService(db)
    svc.set("computer_use_trust_level", body.trust_level)
    svc.set("computer_use_max_steps", str(body.max_steps))
    svc.set("computer_use_plan_timeout_s", str(body.plan_timeout_s))
    svc.set("computer_use_vision_enabled", "true" if body.vision_enabled else "false")
    svc.set("computer_use_audio_enabled", "true" if body.audio_enabled else "false")
    svc.set("computer_use_double_verify", "true" if body.double_verify else "false")
    svc.set("computer_use_browser_enabled", "true" if body.browser_enabled else "false")
    db.commit()
    return body


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

