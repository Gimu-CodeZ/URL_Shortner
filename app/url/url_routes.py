from fastapi import APIRouter, HTTPException, Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse
from app.models.models import URLRequest, URLResponse
from app.url.url_utils import generate_short_code
from app.auth.jwt_handler import decode_access_token
from app.config import collection_url, get_redis_client
from datetime import datetime, timedelta
from app.workers.celery import click_event
import qrcode
from io import BytesIO
import base64

router = APIRouter()
security = HTTPBearer()

RATE_LIMIT = 10
RATE_WINDOW_SECONDS = 3600  # 1 hour


# Dependency to decode JWT token
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


async def check_rate_limit(user_id: str):
    redis_client = get_redis_client()
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis connection not available")

    key = f"rate_limit:{user_id}"
    current_count = redis_client.get(key)

    if current_count is None:
        # First URL creation: set count to 1 with expiry
        redis_client.setex(key, RATE_WINDOW_SECONDS, 1)
        return RATE_LIMIT - 1
    else:
        count = int(current_count)
        if count >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        redis_client.incr(key)
        return RATE_LIMIT - (count + 1)

def generate_qr_code_image(url: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    base64_str = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{base64_str}"

@router.post("/shorten", response_model=URLResponse)
async def shorten_url(url: URLRequest, user_data: dict = Depends(get_current_user)):
    
    remaining_quota = await check_rate_limit(user_data["sub"])

    short_code = generate_short_code()
    while collection_url.find_one({"short_code": short_code}):
        short_code = generate_short_code()

    created_at = datetime.utcnow()
    expire_at = created_at + timedelta(minutes=url.expire_minutes) if url.expire_minutes else None

    new_url = {
        "original_url": str(url.original_url),
        "short_code": short_code,
        "owner_id": user_data["sub"],
        "created_at": datetime.utcnow().isoformat(),
        "expire_at": expire_at.isoformat() if expire_at else None,
        "clicks": 0
    }
    collection_url.insert_one(new_url)

    short_url = f"http://localhost:8000/{short_code}"
    qr_code_base64 = generate_qr_code_image(short_url)

    return {
        "short_url": short_url,
        "remaining_quota": remaining_quota,
        "qr_code": qr_code_base64
    }

@router.get("/{short_code}")
async def redirect_url(short_code: str, request: Request):
    redis_client = get_redis_client()
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis connection is not available")
    
    cached_url = redis_client.get(short_code)
    if cached_url:
        ip_address = request.client.host
        timestamp = datetime.utcnow().isoformat()
        click_event.delay(short_code, ip_address, timestamp)
        return RedirectResponse(url=cached_url)
    
    # Fetch from MongoDB
    url_entry = collection_url.find_one({"short_code": short_code})
    if not url_entry:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    # Check expiration
    expire_at_str = url_entry.get("expire_at")
    if expire_at_str:
        expire_at = datetime.fromisoformat(expire_at_str)
        ttl = (expire_at - datetime.utcnow()).total_seconds()
        if ttl <= 0:
            raise HTTPException(status_code=404, detail="Short URL has expired")
    else:
        ttl = 3600  # Default TTL if no expiration is set
    
    redis_client.setex(short_code, int(ttl), url_entry["original_url"])
    ip_address = request.client.host
    timestamp = datetime.utcnow().isoformat()
    click_event.delay(short_code, ip_address, timestamp)
    return RedirectResponse(url=url_entry["original_url"])
