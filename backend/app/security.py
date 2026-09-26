"""Production himoyasi: soʻrovlar limiti (IP boʻyicha), xavfsizlik sarlavhalari, fayl hajmi chegarasi.

Limitlar xotirada (bitta server uchun yetarli). Bir nechta server boʻlsa — Redis ga koʻchirish kerak.
"""

import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings

WRITE_PREFIXES = ("/verify", "/reports", "/ai/", "/rewards/", "/scan", "/explain", "/customs/", "/ml/packnet/check")
LOGIN_PREFIX = "/auth/login"


class RateLimiter:
    def __init__(self):
        self.hits: dict[tuple[str, str], deque] = defaultdict(deque)

    def allow(self, key: tuple[str, str], limit: int, now: float) -> bool:
        q = self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        if len(self.hits) > 50_000:  # xotira oʻsib ketmasin
            self.hits.clear()
        return True


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    """Haqiqiy mijoz IP si. Backend faqat ichki tarmoqda (127.0.0.1 / docker) tinglaydi va barcha soʻrovlar
    veb-server (Next.js) yoki tunnel orqali keladi — shuning uchun proksi sarlavhalariga ishonamiz."""
    if settings.trust_proxy:
        cf = request.headers.get("cf-connecting-ip")  # Cloudflare qoʻyadi, mijoz soxtalashtira olmaydi
        if cf:
            return cf.strip()
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def bucket(request: Request) -> tuple[str, int] | None:
    path = request.url.path
    if path.startswith(LOGIN_PREFIX):
        return "login", settings.rate_limit_login_per_min
    if request.method == "POST" or path.startswith(WRITE_PREFIXES):
        return "write", settings.rate_limit_write_per_min
    return "read", settings.rate_limit_read_per_min


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.rate_limit_enabled and request.url.path not in ("/health",):
            b = bucket(request)
            if b and not limiter.allow((client_ip(request), b[0]), b[1], time.monotonic()):
                return JSONResponse({"detail": "Juda koʻp soʻrov. Bir daqiqadan keyin qayta urinib koʻring."},
                                    status_code=429, headers={"Retry-After": "60"})
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_upload_mb * 1024 * 1024:
            return JSONResponse({"detail": f"Fayl juda katta (koʻpi bilan {settings.max_upload_mb} MB)."},
                                status_code=413)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def _production_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin.strip())
        port = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme == "https" and parsed.hostname
        and parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        and not parsed.hostname.endswith(".localhost")
        and "*" not in parsed.netloc
        and parsed.username is None and parsed.password is None
        and not parsed.path and not parsed.query and not parsed.fragment
        and (port is None or port > 0)
    )


def check_production_config() -> None:
    """Productionda xavfli standart sozlamalar bilan ishga tushmaslik."""
    if not settings.is_production:
        return
    problems = []
    if len(settings.secret_key) < 32:
        problems.append("SECRET_KEY kamida 32 belgi boʻlishi kerak (masalan: openssl rand -hex 32)")
    if settings.show_demo_accounts:
        problems.append("SHOW_DEMO_ACCOUNTS=false qiling")
    if not settings.auth_enabled:
        problems.append("AUTH_ENABLED=true qiling")
    if settings.seed_on_startup:
        problems.append("SEED_ON_STARTUP=false qiling: productionda demo maʼlumotlar yaratilmaydi")
    if not settings.rate_limit_enabled:
        problems.append("RATE_LIMIT_ENABLED=true qiling")
    if not all(_production_origin(origin) for origin in settings.cors_origins.split(",")):
        problems.append("CORS_ORIGINS ga faqat aniq HTTPS origin yozing (https://domen, yoʻlsiz)")
    if problems:
        raise RuntimeError("Production sozlamalari xato:\n- " + "\n- ".join(problems))
