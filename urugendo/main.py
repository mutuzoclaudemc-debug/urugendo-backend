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
