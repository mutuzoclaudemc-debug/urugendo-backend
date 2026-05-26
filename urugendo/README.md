# 🇷🇼 Urugendo API — Backend

> Rwanda's ridesharing platform. "Urugendo" means **journey** in Kinyarwanda.

Built with **FastAPI + PostgreSQL**. Supports MTN MoMo & Airtel Money payments.

---

## 📁 Project Structure

```
urugendo/
├── main.py                    # FastAPI app & router registration
├── models.py                  # SQLAlchemy DB models
├── schemas.py                 # Pydantic request/response schemas
├── requirements.txt
├── .env.example               # Environment variables template
│
├── core/
│   ├── config.py              # Settings (loaded from .env)
│   ├── database.py            # DB engine, session, Base
│   └── security.py            # JWT, password hashing, auth dependency
│
├── routers/
│   ├── auth.py                # POST /register, /login, GET /me
│   ├── rides.py               # CRUD + search for rides
│   ├── bookings.py            # Book, cancel, confirm, rate
│   └── payments.py            # MTN MoMo & Airtel initiate + webhooks
│
├── services/
│   └── payment_service.py     # MTN & Airtel API calls
│
└── migrations/
    └── 0001_initial.py        # Alembic migration
```

---

## 🚀 Quick Start

### 1. Clone & install dependencies

```bash
git clone https://github.com/yourname/urugendo-api
cd urugendo
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, and payment credentials
```

### 3. Create the database

```bash
# Make sure PostgreSQL is running
createdb urugendo_db

# Run migrations
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive API docs (Swagger UI).

---

## 🔑 Authentication

All protected endpoints require a JWT Bearer token in the header:

```
Authorization: Bearer <your_token>
```

Get a token via `POST /api/auth/login` or `POST /api/auth/register`.

---

## 📡 API Endpoints

### Auth
| Method | Endpoint              | Description             | Auth |
|--------|-----------------------|-------------------------|------|
| POST   | `/api/auth/register`  | Create account          | ❌   |
| POST   | `/api/auth/login`     | Login, get JWT token    | ❌   |
| GET    | `/api/auth/me`        | Get my profile          | ✅   |
| PUT    | `/api/auth/me`        | Update my profile       | ✅   |

### Rides
| Method | Endpoint                  | Description             | Auth |
|--------|---------------------------|-------------------------|------|
| POST   | `/api/rides/`             | Post a ride offer       | ✅   |
| GET    | `/api/rides/search`       | Search rides            | ❌   |
| GET    | `/api/rides/{id}`         | Get ride details        | ❌   |
| GET    | `/api/rides/my/offered`   | My offered rides        | ✅   |
| DELETE | `/api/rides/{id}`         | Cancel my ride          | ✅   |

### Bookings
| Method | Endpoint                          | Description           | Auth |
|--------|-----------------------------------|-----------------------|------|
| POST   | `/api/bookings/`                  | Book a ride           | ✅   |
| GET    | `/api/bookings/my`                | My bookings           | ✅   |
| GET    | `/api/bookings/{id}`              | Booking details       | ✅   |
| POST   | `/api/bookings/{id}/cancel`       | Cancel booking        | ✅   |
| POST   | `/api/bookings/{id}/confirm`      | Driver confirms       | ✅   |
| POST   | `/api/bookings/{id}/rate`         | Rate after trip       | ✅   |

### Payments
| Method | Endpoint                        | Description              | Auth |
|--------|---------------------------------|--------------------------|------|
| POST   | `/api/payments/initiate`        | Start MoMo/Airtel pay    | ✅   |
| GET    | `/api/payments/{id}/status`     | Check payment status     | ✅   |
| POST   | `/api/payments/mtn/callback`    | MTN MoMo webhook         | ❌   |
| POST   | `/api/payments/airtel/callback` | Airtel Money webhook     | ❌   |

---

## 💳 Payment Flow

```
Passenger books ride → POST /bookings/
        ↓
    POST /payments/initiate  (provider: mtn_momo or airtel)
        ↓
    User receives USSD prompt on their phone
        ↓
    User approves on phone
        ↓
    MTN/Airtel calls webhook → booking auto-confirmed
        ↓
    Passenger can also poll GET /payments/{id}/status
```

### MTN MoMo Setup
1. Register at https://momodeveloper.mtn.com
2. Subscribe to **Collections** product
3. Create an API User + API Key
4. Add credentials to `.env`

### Airtel Money Setup
1. Register at https://developers.airtel.africa
2. Create an app, get Client ID + Secret
3. Add credentials to `.env`

---

## 🛡️ Security

- Passwords hashed with **bcrypt**
- Auth via **JWT** (HS256), configurable expiry
- Phone format validated: Rwanda numbers (`+2507XXXXXXXX`)
- Prices in **RWF** (Rwandan Franc), minimum 500 RWF per seat

---

## 🗄️ Database Schema

```
users ──────────────────────────────────────────────────────┐
  id, full_name, phone, email, hashed_password,            │
  is_active, is_verified, avatar_url, bio, created_at      │
                                                            │
rides ──────────────────────────────────────────────────────┤
  id, driver_id→users, origin_city, destination_city,      │
  departure_date, departure_time, total_seats,              │
  available_seats, price_per_seat, car_model, tags          │
                                                            │
bookings ───────────────────────────────────────────────────┤
  id, ride_id→rides, passenger_id→users,                   │
  seats_booked, total_price, status                        │
                                                            │
payments ───────────────────────────────────────────────────┤
  id, booking_id→bookings, provider, phone_number,         │
  amount, external_ref, status, completed_at               │
                                                            │
ratings ────────────────────────────────────────────────────┘
  id, booking_id→bookings, rater_id→users,
  rated_user_id→users, score, comment
```

---

## 🔮 Next Steps

- [ ] SMS notifications (Africa's Talking or Infobip)
- [ ] Phone OTP verification on registration
- [ ] Admin dashboard
- [ ] Real-time seat updates via WebSocket
- [ ] Docker + docker-compose setup
- [ ] Deploy to Railway / Render / AWS Lightsail

---

Made with ❤️ for Rwanda 🇷🇼
