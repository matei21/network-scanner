import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .database import init_db
from .routes import router


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name, "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or default


# Only our own UI may call the API from a browser (security fix).
# "*" let any website open on the demo laptop read the scan history or change
# settings through the user's browser. Override with CORS_ORIGINS if the UI runs
# elsewhere, e.g. CORS_ORIGINS=http://localhost:3000
ALLOWED_ORIGINS = _env_list("CORS_ORIGINS", [
    "http://localhost:5173", "http://127.0.0.1:5173",   # Vite dev server
    "http://localhost:4173", "http://127.0.0.1:4173",   # Vite preview
])

# Only requests addressed to this laptop itself are answered. Blocks "DNS
# rebinding", where a website points its own domain name at 127.0.0.1 to get
# around the browser's checks. "testserver" is the host name FastAPI's test
# client uses. Override with TRUSTED_HOSTS if needed.
TRUSTED_HOSTS = _env_list("TRUSTED_HOSTS", ["localhost", "127.0.0.1", "::1", "testserver"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from ai.ai_service import get_local_llm
    get_local_llm()  # starts loading the model in a background thread; requests never wait on it
    yield


app = FastAPI(
    title="Network Scanner API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,   # the API uses no cookies or logins
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(router, prefix="/api")
