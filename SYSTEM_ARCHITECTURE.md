# MamaBird & Chirpy — Complete System Architecture & Design Document

> **Project:** AI-powered educational chatbot platform for children ages 3–12  
> **Client:** Iris Scarfone — Three Baby Birdies  
> **Developer:** Muhammad Sheharyar Ghori
> **Live URLs:**
> - Website: https://mamabird-chirpy.netlify.app  
> - Backend API: https://web-production-bcff5.up.railway.app  
> - API Docs: https://web-production-bcff5.up.railway.app/docs

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Technology Stack](#3-technology-stack)
4. [Repository Structure](#4-repository-structure)
5. [Backend Architecture](#5-backend-architecture)
6. [Database Schema](#6-database-schema)
7. [AI Integration](#7-ai-integration)
8. [Payment System](#8-payment-system)
9. [Frontend Website](#9-frontend-website)
10. [Mobile Application](#10-mobile-application)
11. [Security Architecture](#11-security-architecture)
12. [Deployment Infrastructure](#12-deployment-infrastructure)
13. [Features Built](#13-features-built)
14. [Features Beyond Requirements](#14-features-beyond-requirements)
15. [Challenges Overcome](#15-challenges-overcome)
16. [API Reference Summary](#16-api-reference-summary)
17. [Cost Breakdown](#17-cost-breakdown)
18. [Remaining Milestones](#18-remaining-milestones)

---

## 1. System Overview

MamaBird & Chirpy is a multi-platform AI educational product consisting of:

- **A marketing & purchase website** (static HTML/CSS/JS, Netlify)
- **A FastAPI backend** (Railway) serving both the website's chatbot widget and the Flutter mobile app
- **A Flutter mobile application** (Android + iOS) with full offline-resilient UI
- **A Supabase PostgreSQL database** with 8 production tables
- **Stripe payment integration** for monthly subscriptions and one-time eBook purchase
- **Claude AI (Anthropic)** powering two AI tutors: Chirpy (playful, child-facing) and Mama Bird (warm, parent-facing)
- **ElevenLabs TTS** for natural voice output in the mobile app

The platform is designed as a **white-label multi-tenant system** — the backend can serve multiple branded deployments (identified by `client_id` + `X-Client-Domain` header) from a single codebase.

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│                                                                  │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │   Website (Netlify) │    │   Flutter App (Android / iOS)    │ │
│  │   HTML / CSS / JS   │    │   Provider + flutter_animate     │ │
│  │   layout.js (shared)│    │   Speech-to-text + ElevenLabs    │ │
│  └──────────┬──────────┘    └────────────────┬─────────────────┘ │
└─────────────┼────────────────────────────────┼───────────────────┘
              │ HTTPS REST                     │ HTTPS REST
              ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (Railway)                              │
│                                                                   │
│  FastAPI  ──►  SlowAPI Rate Limiter                              │
│              ──►  JWT Auth Middleware                             │
│              ──►  Content Sanitizer (sanitizer.py)               │
│              ──►  Tenant Guard (TenantSafeQuery)                 │
│              ──►  Subscription Gate (require_subscription)       │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ /auth    │ │ /chat    │ │ /payments│ │ /dashboard       │   │
│  │ /profiles│ │ /badges  │ │ /ebook   │ │ /admin           │   │
│  │ /lessons │ │ /sessions│ │          │ │ /usage           │   │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └──────────────────┘   │
│                    │             │                                │
│          ┌─────────▼──┐   ┌─────▼──────┐                        │
│          │Circuit     │   │  Stripe    │                        │
│          │Breaker     │   │  SDK       │                        │
│          └─────┬──────┘   └────────────┘                        │
└────────────────┼────────────────────────────────────────────────┘
                 │
    ┌────────────┼───────────────────┐
    ▼            ▼                   ▼
┌────────┐  ┌──────────┐      ┌────────────┐
│Supabase│  │Anthropic │      │ ElevenLabs │
│  DB    │  │Claude API│      │ TTS API    │
│ 8 tbl  │  │Sonnet 4.6│      │            │
└────────┘  └──────────┘      └────────────┘
```

---

## 3. Technology Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| FastAPI | Latest | Web framework |
| Uvicorn | Latest | ASGI server |
| Supabase-py | Latest | Database client |
| Anthropic SDK | ≥0.40.0 | Claude AI |
| python-jose | Latest | JWT tokens |
| passlib | 1.7.4 | Password hashing |
| bcrypt | **3.2.2 (pinned)** | Hash backend |
| SlowAPI | Latest | Rate limiting |
| Stripe SDK | Latest | Payments |
| ReportLab | Latest | PDF generation |
| Pillow | Latest | Image processing |

> ⚠️ **bcrypt must stay at 3.2.2** — version 4.x breaks passlib's internal hash comparison with a "password cannot be longer than 72 bytes" error.
> ⚠️ **Anthropic SDK must be ≥0.40.0** — older versions fail with "unexpected keyword argument 'proxies'" due to httpx breaking changes.

### Frontend Website
| Technology | Purpose |
|---|---|
| Vanilla HTML5/CSS3/JS | No build step, instant Netlify deploy |
| Google Fonts (Quicksand + Nunito) | Typography |
| Lucide Icons (CDN) | Icon system |
| layout.js | Shared nav, footer, floating birds injected on every page |
| IntersectionObserver API | Scroll-reveal animations |
| Stripe.js | Payment redirects |

### Mobile App
| Technology | Version | Purpose |
|---|---|---|
| Flutter | 3.x | Cross-platform framework |
| Dart | 3.x | Language |
| Provider | Latest | State management |
| flutter_animate | Latest | Declarative animations |
| http | Latest | API calls |
| flutter_tts | Latest | Text-to-speech fallback |
| audioplayers | Latest | ElevenLabs audio playback |
| speech_to_text | Latest | Voice input |
| flutter_markdown | Latest | Render AI responses |
| shared_preferences | Latest | Token persistence |

### Infrastructure
| Service | Role | Plan |
|---|---|---|
| Railway | Backend hosting + auto-deploy | Hobby ($5/mo) |
| Netlify | Website hosting + auto-deploy | Free |
| Supabase | PostgreSQL + Auth | Free |
| GitHub | 3 repos + CI trigger | Free |
| Anthropic | Claude AI API | Pay-per-use |
| Stripe | Payments | 2.9% + $0.30/txn |
| ElevenLabs | Voice TTS | Starter $5/mo |

---

## 4. Repository Structure

### `MSheharyar/mamabird-backend`
```
mamabird-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, global exception handler
│   │   ├── limiter.py           # SlowAPI singleton (avoids circular import)
│   │   ├── dependencies.py      # require_subscription(), require_role()
│   │   ├── circuit_breaker.py   # Anthropic API resilience wrapper
│   │   ├── sanitizer.py         # Input sanitization before Claude
│   │   ├── models/              # Pydantic request/response models
│   │   ├── api/
│   │   │   ├── auth.py          # Signup, login, JWT
│   │   │   ├── chat.py          # Claude chat endpoints
│   │   │   ├── profiles.py      # Child profile CRUD
│   │   │   ├── badges.py        # Badge earning + listing
│   │   │   ├── lessons.py       # AI lesson plan generation
│   │   │   ├── sessions.py      # Chat session history
│   │   │   ├── dashboard.py     # Parent dashboard API
│   │   │   ├── payments.py      # Stripe subscriptions + ebook
│   │   │   ├── admin.py         # Iris admin panel API
│   │   │   └── usage.py         # Token/cost usage logs
│   │   └── services/
│   │       └── tenant.py        # TenantSafeQuery (multi-tenant guard)
│   ├── requirements.txt
│   ├── Procfile                 # web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
│   └── .env.example
├── docs/
├── web-widget/                  # Original React widget (superseded by Flutter app)
└── threebabybirdies_prototype/  # (now in separate mamabird-website repo)
```

### `MSheharyar/mamabird-website`
```
threebabybirdies/
├── index.html         # Homepage — KidZo-style hero, subject tiles, eBook promo
├── about.html         # Family story — Iris, Frank, Ronald Scarfone
├── book.html          # Physical book + signed copy order
├── blog.html          # Articles about children's reading
├── chatbot.html       # Chirpy's Classroom feature page
├── pricing.html       # Plan cards (Free / Individual / Premium / Classroom)
├── login.html         # Sign in / Register (red theme)
├── ebook.html         # $4.99 eBook purchase page
├── ebook-download.html # Post-payment download page
├── contact.html       # Contact form
├── payment-success.html
├── privacy.html       # Full GDPR/COPPA privacy policy
├── terms.html         # Terms of service + subscription table
├── coppa.html         # Detailed COPPA compliance disclosure
├── css/main.css       # Full v2 design system (~600 lines)
├── js/layout.js       # Shared nav + footer + floating birds
├── js/main.js         # Page interactions, scroll-reveal
└── assets/            # frontpage.png, author-image.png, frank.jpg
```

### `MSheharyar/mamabird-mobile`
```
mamabird_app/
├── lib/
│   ├── main.dart
│   ├── constants/
│   │   ├── theme.dart    # kRed, kPurple, kSubjectColors, kSubjectEmojis
│   │   └── api.dart      # Base URL constants
│   ├── screens/
│   │   ├── splash_screen.dart    # Red gradient, floating birds, elasticOut
│   │   ├── login_screen.dart     # Red hero header, tab auth
│   │   ├── home_screen.dart      # KidZo subject tiles, real API stats
│   │   ├── chat_screen.dart      # Full AI chat, voice in/out, PIN lock
│   │   ├── badges_screen.dart    # Purple gradient, colored badge cards
│   │   ├── settings_screen.dart  # Purple profile header, PIN dialog
│   │   └── child_profiles_screen.dart
│   └── services/
│       ├── auth_service.dart     # JWT + Provider state
│       ├── api_service.dart      # HTTP client wrapper
│       └── elevenlabs_service.dart # TTS + markdown stripping
├── android/
├── ios/
└── pubspec.yaml
```

---

## 5. Backend Architecture

### Request Lifecycle
```
Request
  → CORS middleware (env-configured origins)
  → SlowAPI rate limiter (per-IP)
  → JWT auth middleware (verify token, inject user)
  → Content sanitizer (strip injections before Claude)
  → TenantSafeQuery guard (filter all DB queries by client_id)
  → require_subscription() / require_role() dependency
  → Business logic
  → Response (stack traces NEVER exposed)
```

### Multi-Tenant Design
Every DB query against user data is filtered by `client_id` via `TenantSafeQuery`. The `client_id` is resolved from the `X-Client-Domain` header. This means the entire backend can serve multiple white-label deployments (e.g., a second school district's chatbot) from the same Railway service by setting different domains.

### Circuit Breaker Pattern
All Claude API calls go through `anthropic_breaker.call()` in `circuit_breaker.py`. If Anthropic's API fails or times out, the breaker opens and requests fast-fail instead of queuing up and timing out users. This prevents cascade failures under load.

### Message Limit Enforcement
```
tier          messages/month
──────────────────────────────
trial         100
individual    400
premium       1,000
classroom     200 (per student profile)
```
Enforced server-side in `require_subscription()` — cannot be bypassed from the client.

---

## 6. Database Schema

### Tables (Supabase PostgreSQL)

#### `client_configs`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| domain | text UNIQUE | e.g. "threebabybirdies.com" |
| brand_name | text | "Three Baby Birdies" |
| chirpy_name | text | "Chirpy" |
| mama_name | text | "Mama Bird" |
| primary_color | text | Hex color |
| created_at | timestamptz | |

#### `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| client_id | UUID FK → client_configs | Multi-tenant key |
| email | text UNIQUE | |
| hashed_password | text | bcrypt 3.2.2 |
| role | text | "parent" \| "teacher" \| "admin" |
| subscription_status | text | "trial" \| "active" \| "grace" \| "past_due" |
| stripe_customer_id | text | |
| messages_used_this_month | int | Reset monthly |
| created_at | timestamptz | |

#### `child_profiles`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| parent_id | UUID FK → users | |
| client_id | UUID FK | |
| nickname | text | NOT real name — COPPA |
| age | int | Optional |
| grade | text | Optional |
| created_at | timestamptz | |

#### `chat_sessions`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| child_profile_id | UUID FK | |
| client_id | UUID FK | |
| character | text | "chirpy" \| "mama" |
| subject | text | One of 6 subjects |
| messages | JSONB | Array of `{role, content}` objects |
| created_at | timestamptz | |
| updated_at | timestamptz | |

#### `progress`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| child_profile_id | UUID FK | |
| session_id | UUID FK | |
| subject | text | |
| total_questions | int | (NOT `total`) |
| correct_answers | int | |
| created_at | timestamptz | |

#### `badges`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| child_profile_id | UUID FK | |
| badge_name | text | |
| badge_type | text | "first_session" \| "streak" \| "subject_mastery" etc. |
| earned_at | timestamptz | |
| metadata | JSONB | Extra context |

> **6 badge rules** — all idempotent (same badge never awarded twice to same child).

#### `lesson_plans`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| child_profile_id | UUID FK | |
| subject | text | |
| content | JSONB | AI-generated structured plan |
| pdf_path | text | Generated PDF location |
| created_at | timestamptz | |

#### `usage_logs`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK | |
| client_id | UUID FK | |
| model | text | "claude-sonnet-4-6" |
| input_tokens | int | |
| output_tokens | int | |
| cost_usd | float | Calculated server-side |
| was_fallback | boolean | Circuit breaker fallback? |
| duration_ms | int | |
| created_at | timestamptz | |

---

## 7. AI Integration

### Model
**Claude Sonnet 4.6** (`claude-sonnet-4-6`) — Anthropic's latest Sonnet. The dated alias `claude-sonnet-4-20250514` is deprecated (retiring June 15, 2026) and has been updated.

### Two AI Tutors

**Chirpy** — upbeat, playful, child-facing. Uses simple vocabulary, encouragement, lots of emoji. Designed for ages 3–8. Subjects: Spelling, Rhyming, Math, Grammar, Puzzles, Stories.

**Mama Bird** — warm, patient, slightly more formal. Designed for when parents want a calmer tone. Same 6 subjects, more explanation, less emoji.

Both tutors are defined via system prompts only — **no hardcoded character names in business logic**. Everything comes from `client_configs.chirpy_name` / `client_configs.mama_name`.

### Safety Pipeline
```
User message
  → sanitizer.py (strip prompt injection, forbidden patterns)
  → System prompt (character persona + subject constraint)
  → Claude API (via circuit breaker)
  → Response
  → Content safety check (post-generation)
  → Delivered to user
```

### Lesson Plan Generation
AI generates structured JSON lesson plans per subject + child age/grade. Plans are:
- Stored in the `lesson_plans` table
- Exportable as PDF via ReportLab
- Downloadable by parent from dashboard

---

## 8. Payment System

### Subscription Tiers (Stripe)
| Plan | Price | Messages | Profiles |
|---|---|---|---|
| Free Trial | $0 / 3 months | 100/mo | 1 |
| Individual | $9.99/mo | 400/mo | 3 |
| Premium | $19.99/mo | 1,000/mo | Unlimited |
| Classroom | $29.99/mo | 200/student | 30 students |

### eBook (One-Time Purchase)
- Price: $4.99
- Flow: `ebook.html` → POST `/payments/ebook-checkout` → Stripe Checkout → `ebook-download.html?session_id=` → GET `/payments/ebook-verify` → download URL
- Uses `mode="payment"` (not subscription) with `price_data` inline (no stored Price ID)
- Verified by `session.payment_status == "paid"` + `metadata.product == "ebook"`

### Webhook Handling
- `customer.subscription.updated` → update `subscription_status`
- `customer.subscription.deleted` → set `"grace"` period
- `invoice.payment_failed` → set `"past_due"`
- Grace period string is always `"grace"` (never `"grace_period"`)

---

## 9. Frontend Website

### Design System
The website uses a custom CSS design system (`css/main.css`) inspired by **KidZo / PlayWize edtech** aesthetics:

- **Color vars:** `--red`, `--sky`, `--yellow`, `--green`, `--purple`, `--orange`, `--cream`
- **Typography:** Quicksand (headings/display) + Nunito (body)
- **Animations:** `@keyframes float`, `blob-drift`, `slide-up`, `marquee` scroll strip
- **Glassmorphism:** `backdrop-filter: blur(12px)` + `rgba(255,255,255,.15)` cards
- **Subject tiles:** Colorful gradient cards with large emoji, `translateY(-7px) scale(1.02)` hover lift
- **Scroll-reveal:** IntersectionObserver with `.reveal` / `.visible` CSS classes
- **Floating birds:** 4 fixed-position `🐦🪺` elements injected by `layout.js` on every page

### Pages
| Page | Purpose | Special features |
|---|---|---|
| `index.html` | Homepage | Animated blobs, stats bar, subject tiles, marquee, eBook promo |
| `chatbot.html` | Public Chirpy's Classroom demo | Character selector, subject tiles, scroll-reveal. **Redirects logged-in users immediately** via `window.location.replace()` to their correct app page — no sign-out button exposed |
| `app.html` | Authenticated parent/teacher app | Full-height chat with Chirpy, parent dashboard panel (progress, badges, lesson plan export). 4-digit PIN lock gates all parent controls |
| `admin.html` | Iris admin dashboard | Stats cards, parents table with expandable child rows, extend-trial / cancel actions, daily usage breakdown, search + status filter |
| `pricing.html` | Plan comparison | Gradient plan cards (4 tiers) |
| `login.html` | Auth | Red gradient, warm background, tab Sign In / Register. Routes to `admin.html` or `app.html` by role after login. Redirects already-logged-in users immediately |
| `ebook.html` | eBook purchase | 3D book mockup, Stripe checkout |
| `ebook-download.html` | Post-payment | Session verify, download button |
| `privacy.html` | Privacy Policy | 10 sections, COPPA callout |
| `terms.html` | Terms of Service | Plan table, refund policy |
| `coppa.html` | COPPA Compliance | Parent rights grid, AI safety |

### Shared Layout (`layout.js`)
- Injects nav, mobile menu, footer into every page via `innerHTML`
- When logged in: swaps nav CTA to "My Classroom →" linking to `app.html` (parents/teachers) or `admin.html` (admin). **Sign out is completely absent from the public nav** — a child cannot sign out from any public page; logout is only accessible via PIN-protected button inside `app.html`
- Injects 4 floating birds with staggered CSS animations (position:fixed, z-index:0)
- Active nav link detection

### Web PIN Lock System (`app.html`)
`app.html` enforces a child-safe mode by default:
- **Child mode** (default): only the chat interface is visible. Dashboard, logout, and all parent controls are hidden behind a `🔒` button
- **Parent mode** (unlocked): revealed by entering the 4-digit PIN in a fullscreen numpad modal
- **First-time setup**: no stored PIN → modal walks parent through set → confirm flow
- **Auto-relock**: parent mode automatically locks after 3 minutes of inactivity
- **Lockout**: 5 failed attempts → 5-minute lockout with countdown
- **Lock-on-close**: dashboard panel locks automatically when closed
- PIN stored as plain 4-digit string in `localStorage` under `mb_pin` (server-side PIN hashing is a future enhancement)

---

## 10. Mobile Application

### Architecture
Flutter with Provider state management. Single `AuthService` ChangeNotifier holds JWT token, user object, child profile ID, and PIN state. All screens listen via `context.watch<AuthService>()`.

### Screen Flow
```
SplashScreen (2.6s)
  → if auth.isLoggedIn → HomeScreen
  → else → LoginScreen

LoginScreen (tab: Sign In | Register)
  → success → HomeScreen

HomeScreen (bottom nav: Home | Badges | Account)
  → subject tile tap → ChatScreen(subject, character)
  → character card tap → ChatScreen(character)
  → nav: Badges → BadgesScreen
  → nav: Account → SettingsScreen

ChatScreen
  → PopScope (blocks back without Parent PIN)
  → Parent PIN dialog (numpad, shake animation)

SettingsScreen
  → Child Profiles → ChildProfilesScreen
  → Badges → BadgesScreen
```

### Voice Pipeline
```
Mic button → SpeechToText → text → API → Claude response
                                              ↓
                           ElevenLabs TTS (natural voice)
                                 ↓ fails/free tier
                           flutter_tts fallback (mobile only)
```

### APK v1.0 (Internal Testing)
- Built June 2026 as debug-signed release APK (50.2 MB) for TechManhattan dev team review
- App label set to **"Chirpy's Classroom"** via `AndroidManifest.xml` (`android:label`)
- Production API URL hardcoded in `api.dart` (`kApiBase = https://web-production-bcff5.up.railway.app`)

### Login Screen Fixes (Chrome Web)
- **Tab clipping on Chrome**: `BoxDecoration` indicator was overflowing on Chrome. Fixed by wrapping `TabBar` in `ClipRRect(borderRadius: BorderRadius.circular(14))` + `indicatorSize: TabBarIndicatorSize.tab` + `indicatorPadding: EdgeInsets.zero`
- **Error message sanitization**: Added `_cleanError()` helper that converts raw `ClientException: Failed to fetch` and HTTP status codes into plain-English messages ("Could not reach the server", "Incorrect email or password", "Too many attempts", etc.)

### Design Language
- **Primary color:** `kRed` (#CC2929) — pill buttons, active states
- **Secondary:** `kPurple` (#7C3AED) — badges, settings headers
- **Subject tiles:** `kSubjectColors` map with 6 gradient pairs
- **Animations:** `flutter_animate` — elasticOut scale, fadeIn, slideY, repeat-reverse float
- **Button shape:** `BorderRadius.circular(50)` pill everywhere

---

## 11. Security Architecture

### Authentication
- JWT tokens signed with `SECRET_KEY` env var (RS256)
- Tokens expire in 7 days
- Passwords hashed with bcrypt 3.2.2 (never stored plain)
- Parent PIN stored hashed separately (4-digit, optional)

### COPPA Compliance
- Children never register — only parents/teachers create accounts
- Child profiles contain only: nickname, age (optional), grade (optional)
- No real names, DOB, contact info, photos collected from children
- Chat messages processed for response generation only — not used for advertising
- Parent right to delete: email request → deletion within 30 days
- No third-party advertising cookies or tracking pixels

### API Security
- All endpoints require JWT except `/auth/signup`, `/auth/login`, `/health`
- Rate limiting: 30 requests/minute on chat endpoints (SlowAPI)
- CORS: origin whitelist from env var (not wildcard in production) + `allow_origin_regex=r"http://localhost:\d+"` for Flutter web local development on any port
- Input sanitization before every Claude API call
- Stack traces never exposed in HTTP responses (global exception handler)
- TenantSafeQuery ensures no cross-tenant data leakage

### Public Demo Security (`/chat/demo`)
The public chatbot demo on `chatbot.html` has a dedicated security stack separate from the authenticated system:

| Control | Detail |
|---|---|
| **Server-side message cap** | 4 messages per IP per hour tracked in Redis (`demo:{ip}` key, 1-hour TTL). Falls back to per-process in-memory counter if `REDIS_URL` is not set. Enforced by returning HTTP 429. |
| **Input sanitization** | New message runs through `sanitize_message()` — 12 prompt-injection regex patterns, control character stripping, length cap (500 chars). |
| **History sanitization** | Each conversation history item is individually run through `sanitize_message()` — items that fail are silently dropped before being sent to Claude. |
| **Post-generation safety** | `check_response_safety()` scans Claude's response for profanity, violence, adult content, credential-fishing phrases, and XSS patterns before the response is returned. Returns a safe fallback if triggered. |
| **XSS prevention (frontend)** | `safeHtml()` escapes `&`, `<`, `>`, `"`, `'` in Claude's response before it's injected into `innerHTML`. User input is also escaped before display. |
| **Rate limiting** | SlowAPI: 10 requests/minute per IP (in addition to the Redis 4/hour demo cap). |
| **No DB writes** | Demo calls leave no trace in Supabase — no sessions, no usage logs, no profiles. |
| **Subject lock** | Backend always uses Chirpy + Spelling regardless of what the frontend sends. |

### Child Protection (Web)
Three vectors through which a child could escape the app were identified and closed:
1. **Public nav "Sign out"** — removed entirely. Logged-in nav only shows "My Classroom →" (no sign-out option)
2. **"My Classroom" nav destination** — previously pointed to `chatbot.html` (public demo with unprotected sign-out). Now routes to `app.html` / `admin.html` by role
3. **`chatbot.html` auth bar** — previously rendered a "Sign out" button when logged in. Now immediately `window.location.replace()`s to the correct app page — the page never renders for logged-in users

### Content Safety
- Pre-generation: keyword/pattern filter in `sanitizer.py`
- System prompt: hard constraints on topics (educational only)
- Post-generation: response safety check before delivery
- Rate limits prevent abuse at scale
- All violations logged to `usage_logs` with `was_fallback` flag

---

## 12. Deployment Infrastructure

### Auto-Deploy Pipeline
```
Code change → git push → GitHub
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
         Netlify                        Railway
    (mamabird-website)            (mamabird-backend)
    Deploy in ~30 seconds         Deploy in ~2 minutes
    Publish dir: .                Root dir: /backend
    No build command              Procfile: uvicorn
```

### Environment Variables (Railway)
```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://wvuhrxjcipguksivildu.supabase.co
SUPABASE_KEY=eyJ...
SECRET_KEY=<jwt secret>
STRIPE_SECRET_KEY=sk_live_...        # pending from Iris
STRIPE_WEBHOOK_SECRET=whsec_...      # pending from Iris
STRIPE_PRICE_ID_INDIVIDUAL=price_... # pending from Iris
STRIPE_PRICE_ID_PREMIUM=price_...    # pending from Iris
STRIPE_PRICE_ID_CLASSROOM=price_...  # pending from Iris
EBOOK_PDF_URL=https://...            # pending — upload PDF to storage
ALLOWED_ORIGINS=https://mamabird-chirpy.netlify.app
REDIS_URL=redis://...                # add Railway Redis plugin → auto-set
```

> **Redis setup**: In Railway dashboard → project → "+ New" → "Database" → "Add Redis". Railway injects `REDIS_URL` automatically. Without it the demo limiter falls back to an in-process memory store (resets on redeploy, not shared across instances).

### Database (Supabase)
- Region: USA (free tier)
- 8 tables, all migrated
- Row-level security enabled
- Backups: Supabase daily snapshots (free tier)

---

## 13. Features Built

### Backend API (Production-Grade)
- [x] Multi-tenant white-label architecture
- [x] JWT authentication (signup / login / token refresh)
- [x] Role-based access (parent / teacher / admin)
- [x] Subscription tier enforcement (4 tiers, server-side)
- [x] Claude AI chat — Chirpy + Mama Bird, 6 subjects
- [x] Circuit breaker (Anthropic API resilience)
- [x] Rate limiting (SlowAPI, per-IP)
- [x] Content safety pipeline (sanitize → constrain → post-check)
- [x] Badge system (6 rule types, idempotent)
- [x] Session history (paginated, filterable)
- [x] AI lesson plan generation (structured JSON + PDF export)
- [x] Parent dashboard API (summary, child detail, usage report)
- [x] Child profile CRUD
- [x] Stripe subscription checkout (3 tiers)
- [x] Stripe webhook handling (subscription lifecycle)
- [x] eBook one-time purchase (Stripe Checkout `mode=payment`)
- [x] eBook payment verification endpoint
- [x] PDF download endpoint (lesson plans)
- [x] Iris admin dashboard API (parent/children overview)
- [x] Token + cost logging to `usage_logs`
- [x] Global exception handler (no stack trace leakage)
- [x] CORS from env variable
- [x] Startup validation
- [x] White-label test endpoint (`GET /test/whitelabel-check`)

### Website (12+ Pages)
- [x] Homepage (KidZo-style redesign, animations, subject tiles)
- [x] About, Book, Blog, Contact pages
- [x] Chirpy's Classroom feature page (character selector, subject tiles) — redirects logged-in users
- [x] **Public demo chatbot** — real Claude AI, Spelling only, 4 msg/IP/hour via Redis, full security stack
- [x] **Authenticated app page (`app.html`)** — full chat + parent dashboard behind 4-digit PIN lock
- [x] **Iris admin dashboard (`admin.html`)** — stats, parent table, extend-trial/cancel, usage breakdown
- [x] Role-based post-login routing (admin → `admin.html`, parent/teacher → `app.html`)
- [x] Pricing page (4-tier gradient cards)
- [x] Login/Register page (red theme, tab UI)
- [x] eBook purchase page ($4.99 Stripe paywall)
- [x] eBook download page (payment verification)
- [x] Privacy Policy (10 sections, COPPA-compliant)
- [x] Terms of Service (subscription table, refund policy)
- [x] COPPA Compliance page (parent rights grid, AI safety disclosure)
- [x] Shared layout (nav, footer, floating birds on every page — sign-out removed from public nav)

### Mobile App (Flutter)
- [x] Splash screen (animated, red gradient)
- [x] Login/Register screen (red hero, tab UI — Chrome tab clipping fixed with ClipRRect + indicatorSize)
- [x] Home screen (KidZo subject tiles, real API stats, greeting)
- [x] Chat screen (AI chat, voice input, TTS output, markdown rendering)
- [x] Parental lock (Parent PIN with numpad + shake animation)
- [x] Badges screen (purple gradient, colored badge cards)
- [x] Settings screen (purple profile header, PIN management)
- [x] Child profiles screen (CRUD)
- [x] ElevenLabs TTS integration (with flutter_tts fallback)
- [x] Speech-to-text voice input
- [x] Subject selector pills in chat
- [x] Character switcher (Chirpy ↔ Mama Bird mid-session)
- [x] Bottom navigation (Home / Badges / Account)
- [x] User-friendly error messages via `_cleanError()` (no raw `ClientException` shown to users)
- [x] **APK v1.0** built for internal testing (debug-signed, app label "Chirpy's Classroom")

---

## 14. Features Beyond Requirements

These features were added beyond the original SOW scope, adding significant value:

| Feature | Where | Why it matters |
|---|---|---|
| **eBook Stripe paywall** | Website + Backend | Additional revenue stream — $4.99 one-time purchase of Iris's PDF |
| **COPPA Compliance page** | Website | Legal protection — required for App Store + schools |
| **Privacy Policy + Terms of Service** | Website | Legal protection — Iris had none before |
| **KidZo-style UI redesign** | Website + App | Professional edtech aesthetic matching market leaders |
| **Floating birds on every page** | Website | Brand consistency, delightful micro-interaction |
| **Glassmorphism design system** | Website | Modern, premium feel without extra libraries |
| **ElevenLabs voice integration** | Flutter app | Natural AI voice output vs robotic flutter_tts |
| **Speech-to-text input** | Flutter app | Kids who can't type can still use Chirpy |
| **Parent PIN numpad lock** | Flutter app | COPPA-aligned parental control, keeps kids in the learning zone |
| **Admin dashboard** | Backend + Website | Iris can monitor all parents/children/usage without DB access |
| **Web PIN lock system** | Website (`app.html`) | Child-safe mode by default — parent controls hidden behind 4-digit PIN with auto-relock, lockout, and first-time setup flow |
| **Role-based post-login routing** | Website | Admin routed to `admin.html`, parent/teacher to `app.html` — prevents children from using admin interface |
| **Child escape route hardening** | Website | Sign out removed from public nav, `chatbot.html` redirects logged-in users, `app.html` requires PIN for all parent actions |
| **CORS regex for Flutter web dev** | Backend | `allow_origin_regex` allows any `localhost:\d+` port — Flutter web picks a random port and was blocked by the origin whitelist |
| **Circuit breaker pattern** | Backend | Production resilience — Anthropic outages don't crash the app |
| **Marquee strip animation** | Website | "Spelling · Rhyming · Math · Grammar · Puzzles · Stories" brand loop |
| **Multi-tenant architecture** | Backend | Platform can be licensed to other edtech clients without code changes |
| **Usage cost logging** | Backend | Iris can track Claude API spend per user |
| **White-label test endpoint** | Backend | `/test/whitelabel-check` — instant multi-tenant verification |
| **Scroll-reveal animations** | Website | Modern UX, matches KidZo/PlayWize quality |
| **3 GitHub repos** | Infrastructure | Clean separation: backend / website / mobile |
| **Auto-deploy pipelines** | Infrastructure | Push to GitHub → live in seconds, no manual deploys |

---

## 15. Challenges Overcome

### 1. bcrypt Version Conflict
**Problem:** bcrypt 4.0+ added strict byte-length validation that broke passlib 1.7.4. Login returned "password cannot be longer than 72 bytes" even for short passwords.  
**Solution:** Pinned `bcrypt==3.2.2` in requirements.txt. This version is stable with passlib 1.7.4.

### 2. Anthropic SDK Breaking Change
**Problem:** Older Anthropic SDK (0.28.0) failed with `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'` because httpx dropped the `proxies` argument.  
**Solution:** Upgraded to `anthropic>=0.40.0`. Also updated model string from deprecated `claude-sonnet-4-20250514` to `claude-sonnet-4-6`.

### 3. Circular Import (main.py ↔ auth.py)
**Problem:** Both `app.main` and `app.api.auth` needed to import the SlowAPI limiter, creating a circular import that crashed the app on startup.  
**Solution:** Created `app/limiter.py` as a singleton module. Both files import from there.

### 4. Supabase Schema Assumption Errors
**Problem:** Multiple Day 2 bugs caused by assuming column names that didn't exist (`role`, `total`, `was_correct`).  
**Solution:** Established rule: always discover real schema via `/rest/v1/` OpenAPI endpoint before writing queries. Caught `total_questions` (not `total`), JSONB `messages` field (not one row per message), missing `was_correct` column.

### 5. Netlify CLI Non-Interactive Mode
**Problem:** `netlify link` failed in non-interactive terminal mode.  
**Solution:** Used `netlify sites:list` to get the site ID, then `netlify link --id <id>` to bypass interactive prompts.

### 6. btn-outline Invisible on Dark Backgrounds
**Problem:** `.btn-outline` CSS class had `background:#fff` which made the "Get a Signed Copy" button invisible on the dark eBook promo section.  
**Solution:** Created `.btn-ghost` class with `background:transparent` and `border: 2px solid rgba(255,255,255,.25)` for use on dark backgrounds specifically.

### 7. Chat Screen Character Switcher
**Problem:** `switchChar()` function updated `.char-btn` class names but the redesigned UI used `.char-card-v2` — so switching characters had no visual effect.  
**Solution:** Updated function to target the new card classes and update the Lucide check icon `data-lucide` attribute dynamically.

### 8. ElevenLabs Free Tier Limitation
**Problem:** Lauren voice (used for Mama Bird) is a paid "Library" voice. Free tier rejected it with a 401.  
**Solution:** Fell back to `flutter_tts` on failure. Infrastructure (BytesSource, AudioPlayer) is complete. Resolution: either create an Instant Voice Clone (free) or upgrade to Starter ($5/mo).

### 9. Flutter withOpacity Deprecation
**Problem:** `withOpacity()` is deprecated in Flutter 3.x, causing analysis warnings throughout.  
**Solution:** Migrated all instances to `withValues(alpha: x)` — the new API.

### 12. CORS Port Mismatch on Flutter Web
**Problem:** Flutter web picks a random port (e.g., `localhost:52341`) but Railway's CORS only allowed `localhost:5173` and `localhost:3000`. Chrome blocked every API call with "ClientException: Failed to fetch."  
**Solution:** Added `allow_origin_regex=r"http://localhost:\d+"` to `CORSMiddleware` in `main.py`. Allows any localhost port in dev while production remains whitelist-only.

### 13. Chat Input Floating Mid-Screen
**Problem:** `app.html` chat input box was floating in the middle of the viewport. Root cause: `chat-msgs` had a fixed `height: 380px` and `body` wasn't filling viewport height.  
**Solution:** Full flex layout — `html,body{height:100%;overflow:hidden;}`, `flex:1` on `.app-body` and `.chat-card`, removed fixed height from `.chat-msgs`, `flex-shrink:0` on `.chat-input-row`.

### 14. Flutter Tab Clipping on Chrome
**Problem:** `TabBar` with `BoxDecoration` indicator overflowed its container on Chrome, clipping the "Sign In" tab label.  
**Solution:** Wrapped `TabBar` in `ClipRRect(borderRadius: BorderRadius.circular(14))` and set `indicatorSize: TabBarIndicatorSize.tab` + `indicatorPadding: EdgeInsets.zero`.

### 15. Nested Git Repo Warning
**Problem:** `threebabybirdies_prototype/threebabybirdies/` is the `mamabird-website` repo (has its own `.git`), nested inside the `mamabird-chatbot` (backend) repo. Running `git add threebabybirdies_prototype/` from the backend repo triggered a git warning and excluded the website files.  
**Solution:** Always `cd` into `threebabybirdies_prototype/threebabybirdies/` and push from there to `MSheharyar/mamabird-website`. Never commit website files from the backend repo.

### 10. Mobile Repo Initial Commit Conflict
**Problem:** `mamabird-mobile` GitHub repo had an auto-generated "Initial commit" (README.md). Local Flutter project couldn't fast-forward merge.  
**Solution:** Removed the local untracked README.md, then used `git merge origin/main --allow-unrelated-histories` to combine the histories before pushing.

### 11. Flutter analyze: BuildContext Across Async Gaps
**Problem:** Multiple screens used `context.read<AuthService>()` or `Navigator.pushReplacementNamed(context, ...)` after `await` calls, triggering `use_build_context_synchronously` lint warnings.  
**Solution:** Captured context-dependent values (token, auth) before any `await`, and used `context.mounted` (not `mounted`) guards post-await.

---

## 16. API Reference Summary

### Auth
```
POST /auth/signup          Register parent or teacher
POST /auth/login           Login, returns JWT
GET  /auth/me              Current user info
```

### Chat
```
POST /chat                 Send message to Chirpy or Mama Bird
GET  /sessions             Paginated session history
GET  /sessions/{id}        Single session with messages
```

### Profiles
```
GET    /profiles           List child profiles for current user
POST   /profiles           Create child profile
PUT    /profiles/{id}      Update nickname/age/grade
POST   /profiles/{id}/delete Delete profile
```

### Badges
```
GET  /badges/{child_id}    List badges for a child profile
```

### Lessons
```
POST /lessons/generate     Generate AI lesson plan
GET  /lessons/{id}/pdf     Download lesson plan as PDF
```

### Dashboard
```
GET  /dashboard/summary          Usage stats (sessions, messages, accuracy)
GET  /dashboard/child/{id}       Detailed child progress
GET  /dashboard/usage-report     Full usage breakdown
```

### Payments
```
POST /payments/subscription-checkout   Start Stripe subscription checkout
POST /payments/webhook                 Stripe webhook handler
POST /payments/ebook-checkout         Start eBook Stripe checkout
GET  /payments/ebook-verify           Verify payment + return download URL
```

### Dashboard
```
GET  /dashboard/summary              Usage stats (sessions, messages, accuracy)
GET  /dashboard/child/{id}           Detailed child progress + badge list
GET  /dashboard/child/{id}/export-pdf  Export child progress report as PDF
GET  /dashboard/usage-report         Full usage breakdown
```

### Admin
```
GET  /admin/stats                    6 aggregate stats (total users, children, sessions, revenue, messages, badges)
GET  /admin/parents-detailed         All parent accounts with nested child rows
GET  /admin/parents                  All parent accounts with child counts
GET  /admin/children                 All child profiles with activity
GET  /admin/usage                    Daily usage breakdown table
PUT  /admin/users/{id}/extend-trial  Add 7 days to trial (body: { days: 7 })
PUT  /admin/users/{id}/cancel        Cancel a user's subscription
```

---

## 17. Cost Breakdown

### Monthly at current scale (~0–50 active users)
| Service | Cost/month |
|---|---|
| Railway (Hobby) | $5 + ~$2–5 usage |
| Netlify | $0 (static site, free tier) |
| Supabase | $0 (free tier) |
| Anthropic Claude API | ~$10–30 |
| Stripe | 2.9% + $0.30 per transaction |
| ElevenLabs | $5 (Starter) or $22 (Creator) |
| Domain (threebabybirdies.com) | ~$1/mo |
| **Total** | **~$25–65/month** |

### At scale (500+ active users)
| Service | Cost/month |
|---|---|
| Railway | ~$20–40 |
| Supabase | $25 (Pro) |
| Anthropic Claude API | ~$100–200 |
| Everything else | ~$30 |
| **Total** | **~$175–295/month** |

---

## 18. Remaining Milestones

### Pending (Client-side blockers)
- [ ] Iris provides live Stripe keys (`sk_live_`, `whsec_`, 3 Price IDs)
- [ ] Iris uploads PDF to storage → set `EBOOK_PDF_URL` on Railway
- [ ] ElevenLabs: create Instant Voice Clone or upgrade to Starter plan

### Pending (Developer)
- [ ] Content safety test log (10 prompts → `backend/tests/content_safety_log.md`)
- [ ] Iris admin runbook / Google Doc
- [x] APK v1.0 built (debug-signed, "Chirpy's Classroom", 50.2 MB) — internal testing
- [ ] Google Play submission (signed release APK + store listing)
- [ ] Apple App Store submission ($99/yr developer account)
- [ ] Railway upgrade to Hobby plan (trial ends ~July 23, 2026)
- [ ] Fix `"grace_period"` vs `"grace"` discrepancy in `dependencies.py` webhook handler
- [ ] Token refresh endpoint (`POST /auth/refresh`)
- [ ] Password reset flow (`POST /auth/forgot-password`)

### Future Enhancements (Post-MVP)
- Classroom teacher dashboard (student progress grid)
- Push notifications (badge earned, streak reminders)
- Offline mode (cache last 5 sessions)
- In-app subscription management (cancel without emailing)
- Multi-language support (Spanish first)
- Spline 3D animations on website

---