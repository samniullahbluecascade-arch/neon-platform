# Neonizer Platform

An AI-powered neon sign measurement and quoting platform for sign manufacturers. Upload a logo, get a photorealistic neon mockup, precise tube length measurements, and production-ready quotes in under 60 seconds.

## 🚀 Features

- **AI Mockup Generation** — Transform flat logos into photorealistic LED neon mockups
- **Tube Extraction & Measurement** — Computer vision pipeline traces every tube, counts every bend
- **Instant Quoting** — Automatic pricing based on tube length, materials, and labor
- **Multi-Format Support** — PNG, JPG, SVG, CDR (CorelDraw) files
- **REST API** — Integrate into existing shop software or CRM
- **Billing & Subscriptions** — Stripe-powered payment processing

## 🏗️ Architecture

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 5.x, Django REST Framework, Celery |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS |
| **Database** | PostgreSQL (production), SQLite (local dev) |
| **Cache/Queue** | Redis |
| **AI/ML** | OpenCV, scikit-image, scikit-learn, Gemini API |
| **Billing** | Stripe + dj-stripe |
| **Auth** | JWT (SimpleJWT) + django-allauth |

### Project Structure

```
neon_platform/
├── neon_platform/          # Django project settings
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── development.py    # Local dev settings
│   │   ├── production.py   # Production settings
│   │   └── staging.py      # Staging settings
│   ├── urls.py             # URL routing
│   ├── wsgi.py             # WSGI entry point
│   └── celery.py           # Celery configuration
├── users/                  # User authentication & profiles
├── measurements/           # Core measurement API & V8 engine integration
├── billing/                # Stripe subscriptions & webhooks
├── frontend/               # Next.js frontend application
├── media/                  # Uploaded images (mockups, BW sketches)
├── templates/              # Django templates
├── docker-compose.yml      # Local Docker setup
├── requirements.txt        # Python dependencies
└── vercel.json             # Vercel deployment config
```

### V8 Measurement Engine

The V8 engine is a sophisticated computer vision pipeline for measuring neon tube length:

1. **Input Layer** (`v8_input.py`) — Format detection, normalization, calibration
2. **Ridge Extraction** (`v8_ridge.py`) — Skeletonization, Frangi filter, IR-MST graph building
3. **Geometry Measurement** (`v8_geometry.py`) — Three-regime measurement (straight/arc/freeform)
4. **ML Correction** (`v8_ml_*.py`) — Residual error correction using trained models
5. **Pipeline Orchestration** (`v8_pipeline.py`) — Physics validation, tier assignment

See [V8_Technical_Architecture.md](V8_Technical_Architecture.md) for detailed technical documentation.

## 🛠️ Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 (optional, SQLite works for local dev)
- Redis 7 (optional, required for Celery tasks)

### Option 1: Docker (Recommended)

The fastest way to get started with all services:

```bash
# Clone the repository
git clone https://github.com/yourusername/neon-platform.git
cd neon-platform

# Copy environment file
cp .env.example .env

# Edit .env with your API keys (see Configuration section below)

# Start all services
docker-compose up --build

# Run migrations in a separate terminal
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

Services will be available at:
- **Django API**: http://localhost:8000
- **Frontend**: http://localhost:3000 (run separately, see below)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Option 2: Manual Setup

#### Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration section)

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Start Django server
python manage.py runserver
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment
cp .env.local.example .env.local

# Start development server
npm run dev
```

#### Celery Workers (Optional)

For background job processing:

```bash
# Terminal 1: Start worker
celery -A neon_platform worker --loglevel=info --concurrency=2

# Terminal 2: Start scheduler (for periodic tasks)
celery -A neon_platform beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## ⚙️ Configuration

### Required Environment Variables

Create a `.env` file from `.env.example`:

```env
# ── Django ────────────────────────────────────────────────────────────────────
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ── Database ──────────────────────────────────────────────────────────────────
# SQLite for quick local dev:
DATABASE_URL=sqlite:///db.sqlite3
# Postgres (used in Docker):
# DATABASE_URL=postgres://neon:neon_dev_pw@db:5432/neon_platform

# ── Redis / Celery ────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Stripe ────────────────────────────────────────────────────────────────────
STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_LIVE_SECRET_KEY=sk_live_...
STRIPE_LIVE_MODE=False
DJSTRIPE_WEBHOOK_SECRET=whsec_...

# ── Gemini (V8 engine) ────────────────────────────────────────────────────────
GEMINI_API_KEY=your-gemini-api-key

# ── V8 engine location ────────────────────────────────────────────────────────
# Path to the folder containing v8_pipeline.py
V8_ENGINE_PATH=../Shopify App Development

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Getting API Keys

1. **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Stripe Keys**: Get from [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
3. **Django Secret Key**: Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`

## 📡 API Documentation

### Authentication

All API endpoints (except public ones) require JWT authentication:

```bash
# Get token
POST /api/token/
{
  "email": "user@example.com",
  "password": "password"
}

# Use token in headers
Authorization: Bearer <access_token>
```

### Core Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/token/` | POST | Get JWT access/refresh tokens | No |
| `/api/token/refresh/` | POST | Refresh access token | No |
| `/api/register/` | POST | Create new account | No |
| `/api/jobs/` | POST | Create measurement job | Yes |
| `/api/jobs/` | GET | List user's jobs | Yes |
| `/api/jobs/{id}/` | GET | Get job result | Yes |
| `/api/generate_mockup` | POST | Generate mockup from logo | No |
| `/api/generate_bw` | POST | Convert mockup to B&W sketch | No |
| `/api/full_pipeline` | POST | Logo → Mockup → B&W → Measurement | No |
| `/api/bw_only_pipeline` | POST | Mockup → B&W → Measurement | No |
| `/api/measure` | POST | Direct measurement (legacy) | No |
| `/api/billing/plans/` | GET | List subscription plans | Yes |
| `/api/billing/subscribe/` | POST | Create subscription | Yes |

### Example: Full Pipeline

```bash
curl -X POST http://localhost:8000/api/full_pipeline \
  -F "logo=@customer_logo.png" \
  -F "background=@wall_bg.jpg" \
  -F "width_inches=24" \
  -F "height_inches=12" \
  -F "additional=Outdoor, warm white glow, wall-mounted" \
  -F "uv=Acrylic backboard with logo"
```

Response:
```json
{
  "mockup_b64": "<base64-encoded-png>",
  "bw_b64": "<base64-encoded-png>",
  "measurement": {
    "measured_m": 3.12,
    "tier": "GLASS_CUT",
    "confidence": 0.95,
    "estimated_price": 31.20,
    "shipping_cost": 15.00,
    "total_price": 46.20,
    "n_paths": 14,
    "n_bends": 22,
    "overlay_b64": "<base64-visualization>"
  }
}
```

## 🚢 Deployment


#### Option 1: DigitalOcean / AWS / GCP

For production deployment with full control:

```bash
# Example: Docker deployment on any VPS
docker build -t neon-platform .
docker run -d \
  -p 8000:8000 \
  -v /host/media:/app/media \
  --env-file .env \
  neon-platform
```

#### Option 2: Frontend on Vercel + Backend Elsewhere

You CAN deploy the Next.js frontend to Vercel's free tier:

```bash
cd frontend
vercel --prod
```

Then point the frontend to your backend API:
```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

### Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=False` in environment
- [ ] Change `SECRET_KEY` to a secure random string
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up Stripe live keys and webhooks
- [ ] Configure Sentry for error monitoring
- [ ] Set up persistent file storage (S3, Cloudinary, or volume)
- [ ] Configure SSL/TLS certificates
- [ ] Set up database backups
- [ ] Configure Celery with a production broker (Redis Cloud, CloudAMQP)

## 🧪 Testing

```bash
# Run Django tests
python manage.py test

# Run specific app tests
python manage.py test measurements

# Run with coverage
coverage run manage.py test
coverage report
```

## 📊 Batch Evaluation

Evaluate V8 engine accuracy against ground truth dataset: