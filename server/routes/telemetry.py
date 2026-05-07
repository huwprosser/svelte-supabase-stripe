from datetime import datetime, timezone

from fastapi import APIRouter, Header, Request

from database import telemetry_actions, users
from routes.user import current_user
from schemas import TelemetryAction

router = APIRouter()
DEVICE_HEADERS = [
    "user-agent",
    "sec-ch-ua",
    "sec-ch-ua-platform",
    "sec-ch-ua-mobile",
    "accept-language",
]
MAX_DEVICE_HEADER_LENGTH = 500


def device_info(request: Request) -> dict[str, str]:
    return {
        name: value[:MAX_DEVICE_HEADER_LENGTH]
        for name in DEVICE_HEADERS
        if (value := request.headers.get(name))
    }


@router.post("/telemetry/action")
def track_action(
    body: TelemetryAction,
    request: Request,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    doc = users.find_one({"_id": user.id}) or {}
    if not doc.get("tracking_enabled", False):
        return {"ok": True, "tracked": False}

    telemetry_actions.insert_one(
        {
            "user_id": user.id,
            "action": body.action,
            "session_id": body.session_id,
            "metadata": body.metadata,
            "device": device_info(request),
            "timestamp": datetime.now(timezone.utc),
        }
    )
    return {"ok": True, "tracked": True}
