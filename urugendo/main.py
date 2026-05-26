from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import Base, engine
from routers import auth, bookings, payments, rides

# ── Create all tables ──────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description=(
        "🇷🇼 Rwanda's ridesharing platform — share rides across the country.\n\n"
        "## Features\n"
        "- **Auth** – Phone-based registration & JWT login\n"
        "- **Rides** – Post and search rides between Rwandan cities\n"
        "- **Bookings** – Reserve seats, confirm, cancel\n"
        "- **Payments** – MTN MoMo & Airtel Money integration\n"
        "- **Ratings** – Rate drivers and passengers after trips\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,     prefix="/api")
app.include_router(rides.router,    prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(payments.router, prefix="/api")


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/debug/token", tags=["Debug"])
def debug_token(token: str):
    import jwt as pyjwt, time
    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return {"status": "valid", "payload": payload, "jwt_version": pyjwt.__version__}
    except Exception as e:
        test_token = pyjwt.encode({"sub": 99, "exp": int(time.time()) + 3600}, settings.SECRET_KEY, algorithm="HS256")
        try:
            pyjwt.decode(test_token, settings.SECRET_KEY, algorithms=["HS256"])
            self_sign_ok = True
        except Exception:
            self_sign_ok = False
        return {"status": "error", "error": str(e), "type": type(e).__name__, "jwt_version": pyjwt.__version__, "self_sign_ok": self_sign_ok}
