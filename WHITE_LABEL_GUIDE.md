# White-Label Integration Guide
## Chirpy's Classroom AI Tutoring Platform
### For Organizations, Schools & Development Partners

**Prepared by:** TechManhattan Development Team  
**Product:** Chirpy's Classroom — Powered by Three Baby Birdies & Claude AI  
**Version:** 1.0 | June 2026  
**Contact:** iris@threebabybirdies.com

---

## Table of Contents

1. [What Is White-Labeling?](#1-what-is-white-labeling)
2. [What Your Organization Gets](#2-what-your-organization-gets)
3. [Architecture Overview](#3-architecture-overview)
4. [What Can Be Customized](#4-what-can-be-customized)
5. [Integration Options](#5-integration-options)
6. [API Reference](#6-api-reference)
7. [Web Integration — Step by Step](#7-web-integration--step-by-step)
8. [Mobile Integration — Flutter SDK](#8-mobile-integration--flutter-sdk)
9. [Onboarding Process](#9-onboarding-process)
10. [Data Isolation & Multi-Tenancy](#10-data-isolation--multi-tenancy)
11. [Security & COPPA Compliance](#11-security--coppa-compliance)
12. [Subscription Tiers & Pricing](#12-subscription-tiers--pricing)
13. [SLA & Support](#13-sla--support)
14. [FAQ](#14-faq)

---

## 1. What Is White-Labeling?

White-labeling means your organization gets the **full Chirpy's Classroom AI tutoring engine** — the AI characters, learning subjects, progress tracking, parent dashboard, admin controls, and payment infrastructure — running under **your brand, your domain, your character names, and your color palette**.

Your users never see "Three Baby Birdies" or "Chirpy" unless you choose to. They see your product.

Everything is powered by the same production backend running on Railway at `https://web-production-bcff5.up.railway.app`, and the same Claude Sonnet AI model. You configure your tenant once; after that, every API call, every chat session, every lesson plan automatically reflects your brand.

### What this is NOT

- It is not a chatGPT wrapper you have to prompt yourself
- It is not a raw API you have to build a learning system on top of
- It is not a shared database — your data is fully isolated from all other tenants

---

## 2. What Your Organization Gets

| Capability | Included |
|---|---|
| AI tutoring chat (2 characters) | ✓ |
| 6 learning subjects | ✓ |
| Custom character names & personalities | ✓ |
| Custom brand colors & logo | ✓ |
| Custom domain (your.domain.com) | ✓ |
| Parent/teacher dashboard | ✓ |
| Child profile management | ✓ |
| Progress tracking & badges | ✓ |
| AI lesson plan generation (PDF) | ✓ |
| Session history (paginated) | ✓ |
| Admin dashboard (your admin user) | ✓ |
| Subscription tier enforcement | ✓ |
| COPPA-compliant data handling | ✓ |
| Web embed (iframe or full page) | ✓ |
| Mobile app (Flutter, iOS + Android) | ✓ (source delivery or APK) |
| API access (REST, JWT auth) | ✓ |
| Rate limiting & abuse prevention | ✓ |
| 99.9% uptime SLA (Railway Hobby+) | ✓ |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR ORGANIZATION                     │
│                                                         │
│  Web App           Mobile App          Admin Panel      │
│  (your domain)     (your brand)        (your staff)     │
│       │                 │                   │           │
└───────┼─────────────────┼───────────────────┼───────────┘
        │                 │                   │
        ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│              Chirpy's Classroom API (Railway)            │
│                                                         │
│  POST /auth/login          POST /chat                   │
│  GET  /profiles            GET  /dashboard/summary      │
│  GET  /badges/{child_id}   POST /lessons/generate       │
│  GET  /admin/stats         POST /payments/checkout      │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Multi-Tenant Layer                  │   │
│  │                                                  │   │
│  │  client_configs table (your tenant row)          │   │
│  │  • character_1_name  = "Your Character Name"    │   │
│  │  • character_1_voice = "your personality desc"  │   │
│  │  • theme_colors      = your brand palette       │   │
│  │  • enabled_subjects  = subjects you want active │   │
│  │  • forbidden_topics  = your content rules       │   │
│  │  • knowledge_base    = your curriculum content  │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Claude AI   │  │   Supabase   │  │    Redis     │  │
│  │  Sonnet 4.6  │  │  (isolated   │  │  (rate limit │  │
│  │              │  │   per tenant)│  │   & caching) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Key principle:** The API never reads a brand name, character name, or color from code. Every response is built from your `client_configs` row in the database. Changing your character's name in the database changes it everywhere — in AI responses, in lesson plans, in the mobile app — instantly.

---

## 4. What Can Be Customized

### 4.1 AI Characters

Each tenant gets two AI characters:

| Field | Description | Example |
|---|---|---|
| `character_1_name` | Name of the child-facing tutor | `"Chirpy"`, `"Byte"`, `"Spark"` |
| `character_1_voice` | Personality description (baked into system prompt) | `"playful, enthusiastic, uses lots of emoji"` |
| `character_2_name` | Name of the parent/teacher-facing guide | `"Mama Bird"`, `"Professor Oak"`, `"Coach"` |
| `character_2_voice` | Personality description | `"warm, professional, structured lesson plans"` |

The AI reads these fields and adapts its entire personality — greeting style, vocabulary, sign-off phrases, emoji usage — automatically.

### 4.2 Learning Subjects

Enable any combination of the 6 built-in subjects:

| Subject | What the AI does |
|---|---|
| `spelling` | Word-by-word drill, phonics breakdown, difficulty escalation |
| `math` | Story-based arithmetic problems, step-by-step correction |
| `rhyming` | Phonemic awareness games, rhyme chain building |
| `grammar` | Fill-in-the-blank, parts of speech, sentence construction |
| `puzzles` | Riddles, word scrambles, logic puzzles with hints |
| `literature` | Story comprehension, story starters, creative writing prompts |

Set `enabled_subjects` to any subset. Users cannot access subjects not in this list.

Custom subjects can be added on request — contact us with your curriculum requirements.

### 4.3 Content Rules

```json
{
  "forbidden_topics": [
    "violence",
    "adult_content",
    "politics",
    "weapons",
    "drugs",
    "competitor_brands"     ← you can add your own
  ],
  "fallback_message": "Let's stay focused on our learning adventure!"
}
```

Any message that touches a forbidden topic receives your fallback message instead of an AI response.

### 4.4 Knowledge Base

Inject custom facts, curriculum standards, or brand information that the AI will reference:

```json
{
  "knowledge_base": {
    "school_name": "Westlake Elementary",
    "curriculum_standard": "Common Core Grade 1-3",
    "preferred_reading_level": "Fountas & Pinnell Level D-J",
    "teacher_name": "Ms. Thompson",
    "class_mascot": "Rocky the Raccoon"
  }
}
```

The AI weaves these facts naturally into its responses and lesson plans.

### 4.5 Brand Colors

```json
{
  "theme_colors": {
    "primary": "#0052CC",
    "secondary": "#FFB800",
    "accent": "#00875A"
  }
}
```

Used by the mobile app and web embed to match your brand palette automatically.

### 4.6 Subscription Tiers

You can define your own tier names and limits, or inherit the default structure:

```json
{
  "subscription_tiers": {
    "trial":     { "messages_per_month": 100, "max_profiles": 1, "duration_days": 90 },
    "basic":     { "messages_per_month": 400, "max_profiles": 3 },
    "premium":   { "messages_per_month": 1000, "max_profiles": 999 },
    "classroom": { "messages_per_month": 6000, "max_profiles": 30 }
  }
}
```

---

## 5. Integration Options

### Option A — Full White-Label Website
We deliver the complete website source (HTML/CSS/JS) re-skinned in your brand. You host it on Netlify, Vercel, or your own server. Includes all pages: homepage, chatbot, pricing, login, legal.

**Best for:** Organizations that want a standalone product with their own domain.

### Option B — Embed Widget (iframe)
Drop a single `<iframe>` into any existing website or LMS (Canvas, Schoology, Google Classroom):

```html
<iframe
  src="https://your-tenant.mamabird-chirpy.netlify.app/app.html?embed=true&token=USER_JWT"
  width="100%"
  height="700px"
  style="border:none;border-radius:12px;"
  allow="microphone"
></iframe>
```

The `token` parameter accepts a JWT issued by your own auth system — the backend validates it against your tenant. The `microphone` permission allows voice input.

**Best for:** Schools that want to embed the tutor inside an existing portal.

### Option C — API-First Integration
Call our REST API directly from your own frontend (React, Vue, Next.js, etc.). You own the UI entirely; we provide the AI, progress tracking, and data.

```javascript
// Minimal integration example
const response = await fetch('https://web-production-bcff5.up.railway.app/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${userJwt}`
  },
  body: JSON.stringify({
    message: userInput,
    child_profile_id: childId,
    character: 'character_1',
    subject: 'spelling'
  })
});
const { response: aiReply, new_badges, progress } = await response.json();
```

**Best for:** Dev teams that want full UI control (like TechManhattan building a custom frontend).

### Option D — Mobile App (Flutter)
We deliver the Flutter source code or a compiled APK/IPA. The app reads your tenant config at runtime — character names, colors, subjects — from the API. One codebase serves all tenants.

**Best for:** Organizations that want a standalone iOS/Android app in the App Store under their brand.

---

## 6. API Reference

**Base URL:** `https://web-production-bcff5.up.railway.app`

All authenticated endpoints require:
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

JWTs are obtained from `POST /auth/login` and expire after 7 days.

---

### Authentication

#### Register a parent or teacher
```
POST /auth/signup
```
```json
{
  "email": "parent@example.com",
  "password": "securepassword",
  "role": "parent"
}
```
**Roles:** `parent` | `teacher` | `admin`

#### Login
```
POST /auth/login
```
```json
{ "email": "parent@example.com", "password": "securepassword" }
```
**Response:**
```json
{
  "token": "eyJ...",
  "user": {
    "id": "uuid",
    "email": "parent@example.com",
    "role": "parent",
    "subscription_status": "trial",
    "subscription_plan": null
  }
}
```

#### Current user info
```
GET /auth/me
```

---

### Child Profiles

#### List profiles
```
GET /profiles
```

#### Create profile
```
POST /profiles
```
```json
{
  "child_name": "Alex",
  "age": 7,
  "grade": "Grade 2"
}
```
> COPPA note: `child_name` is a nickname only — never a legal name. No DOB, contact info, or photos are stored for children.

#### Update profile
```
PUT /profiles/{id}
```

#### Delete profile
```
POST /profiles/{id}/delete
```

---

### Chat

#### Send a message
```
POST /chat
```
```json
{
  "message": "CAT",
  "child_profile_id": "uuid",
  "character": "character_1",
  "subject": "spelling"
}
```
**Response:**
```json
{
  "response": "Tweet tweet! YES!! C-A-T — you got it PERFECT! ⭐⭐⭐ Next word: B-I-R-D — can you spell it?",
  "progress": { "score": 1, "total": 1, "topic": "spelling - cat", "was_correct": true },
  "new_badges": [],
  "session_id": "uuid",
  "fallback": false
}
```

**Character values:** `"character_1"` (child tutor) | `"character_2"` (parent/teacher guide)

**Rate limit:** 15 requests/minute per IP. Subscription tiers also enforce monthly message caps.

**Error codes:**
| Code | Meaning |
|---|---|
| `400 UNSAFE_INPUT` | Message contained prompt injection or forbidden content |
| `402 MESSAGE_LIMIT_REACHED` | Monthly message cap hit — user must upgrade |
| `403` | JWT expired or invalid |
| `429` | Rate limit exceeded — wait 1 minute |

---

### Session History

#### List sessions (paginated)
```
GET /sessions?page=1&limit=20&subject=spelling
```

#### Get single session with full messages
```
GET /sessions/{session_id}
```

---

### Progress & Badges

#### Get badges for a child
```
GET /badges/{child_profile_id}
```
**Response:**
```json
[
  {
    "badge_name": "Spelling Star",
    "badge_type": "subject_mastery",
    "earned_at": "2026-06-20T14:32:00Z",
    "metadata": { "subject": "spelling", "sessions_completed": 5 }
  }
]
```

**Badge types:** `first_session` | `streak` | `subject_mastery` | `perfect_score` | `speed_demon` | `explorer`

---

### Dashboard (Parent / Teacher)

#### Usage summary
```
GET /dashboard/summary
```
Returns total sessions, messages sent, average accuracy, active subjects.

#### Detailed child progress
```
GET /dashboard/child/{child_profile_id}
```
Returns per-subject breakdown, recent sessions, badge list, accuracy trend.

#### Export PDF progress report
```
GET /dashboard/child/{child_profile_id}/export-pdf
```
Returns a binary PDF suitable for download or email attachment.

#### Full usage report
```
GET /dashboard/usage-report
```

---

### Lesson Plans

#### Generate AI lesson plan
```
POST /lessons/generate
```
```json
{
  "subject": "spelling",
  "grade": "Grade 2",
  "duration": "5 days",
  "focus_areas": "CVC words, sight words from Dolch list"
}
```
Returns a structured JSON plan with daily activities, objectives, assessment methods, and parent tips.

#### Download lesson plan as PDF
```
GET /lessons/{lesson_id}/pdf
```

---

### Payments

#### Start subscription checkout (Stripe)
```
POST /payments/subscription-checkout
```
```json
{ "plan": "individual" }
```
Returns a Stripe Checkout URL. Redirect user there.

#### eBook one-time purchase
```
POST /payments/ebook-checkout
```

#### Verify eBook payment
```
GET /payments/ebook-verify?session_id=cs_...
```

---

### Admin (Your Admin User)

#### Platform stats
```
GET /admin/stats
```
Returns 6 aggregate numbers: total users, children, sessions, revenue, messages, badges.

#### All parents with child rows
```
GET /admin/parents-detailed
```

#### Extend a user's trial
```
PUT /admin/users/{user_id}/extend-trial
```
```json
{ "days": 7 }
```

#### Cancel a subscription
```
PUT /admin/users/{user_id}/cancel
```

#### Daily usage breakdown
```
GET /admin/usage
```

---

### Public Demo (No Auth)

#### Demo chat — Spelling only, 4 messages per IP per hour
```
POST /chat/demo
```
```json
{
  "message": "CAT",
  "history": [
    { "role": "assistant", "content": "Can you spell C-A-T?" }
  ]
}
```
```json
{
  "response": "Tweet tweet! YES!! Perfect spelling! ⭐",
  "fallback": false,
  "remaining": 3
}
```
**Rate limits:** 10/minute (SlowAPI) + 4 messages/IP/hour (Redis). Returns `429` when exhausted.

---

## 7. Web Integration — Step by Step

### Step 1: We provision your tenant

We insert a row into `clients` and `client_configs` in the production Supabase instance:

```sql
-- clients table
INSERT INTO clients (name, domain, active)
VALUES ('Your Organization', 'app.yourorganization.com', true);

-- client_configs table
INSERT INTO client_configs (client_id, character_1_name, character_1_voice, ...)
VALUES ('<uuid>', 'Spark', 'enthusiastic and encouraging', ...);
```

### Step 2: Set your domain in ALLOWED_ORIGINS

We add `https://app.yourorganization.com` to the `ALLOWED_ORIGINS` environment variable on Railway. This allows CORS from your domain.

### Step 3: User registration

Your app calls `POST /auth/signup`. The backend reads the domain from the `Referer` or `Origin` header, matches it to your tenant row in `clients`, and stamps every user and child profile with your `client_id`. All data is isolated from all other tenants from this point forward.

### Step 4: Integrate the chat UI

Minimum HTML/JS integration:

```html
<!DOCTYPE html>
<html>
<head><title>Your AI Tutor</title></head>
<body>
<div id="messages"></div>
<input id="input" type="text" placeholder="Type here...">
<button onclick="send()">Send</button>

<script>
const API    = 'https://web-production-bcff5.up.railway.app';
const token  = localStorage.getItem('auth_token');
const childId = localStorage.getItem('child_profile_id');

async function send() {
  const msg = document.getElementById('input').value.trim();
  if (!msg) return;
  document.getElementById('input').value = '';

  const res = await fetch(API + '/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({
      message: msg,
      child_profile_id: childId,
      character: 'character_1',
      subject: 'spelling'
    })
  });

  const data = await res.json();

  if (res.status === 402) {
    // Message limit hit — show upgrade prompt
    showUpgradePrompt();
    return;
  }

  const el = document.createElement('p');
  // Always escape AI output before injecting into DOM
  el.textContent = data.response;
  document.getElementById('messages').appendChild(el);
}
</script>
</body>
</html>
```

> **Security note:** Always use `textContent` (not `innerHTML`) when rendering API responses to prevent XSS. If you need to render line breaks, use a DOM-safe method — not `innerHTML` with raw API text.

### Step 5: Handle message limits

```javascript
if (res.status === 402) {
  const err = await res.json();
  // err.detail.code === "MESSAGE_LIMIT_REACHED"
  // err.detail.limit = 100
  // err.detail.current = 100
  showUpgradeModal({ plan: 'individual', price: '$9.99/mo' });
}
```

### Step 6: Display badges

After each `/chat` response, check `data.new_badges`:
```javascript
if (data.new_badges && data.new_badges.length > 0) {
  data.new_badges.forEach(badge => {
    showBadgeToast(badge.badge_name); // e.g. "Spelling Star 🌟"
  });
}
```

---

## 8. Mobile Integration — Flutter SDK

### 8.1 What we deliver

- Full Flutter source code (Dart, null-safe, Flutter 3.x)
- Pre-configured `api.dart` pointing to the production backend
- `AuthService` (Provider-based state management)
- All screens: Login, Home, Chat, Badges, Settings, Child Profiles
- `kApiBase` constant — change one line to point to your API if self-hosted

### 8.2 Configuring your tenant

In `lib/constants/api.dart`:
```dart
const String kApiBase = 'https://web-production-bcff5.up.railway.app';
// Change to your self-hosted URL if applicable
```

The app reads character names, colors, and enabled subjects from the backend at login time — no hardcoded brand values in the app source.

### 8.3 Key Flutter files

| File | Purpose |
|---|---|
| `lib/constants/api.dart` | Base URL, endpoint paths |
| `lib/services/auth_service.dart` | JWT storage, login/logout, user state |
| `lib/screens/login_screen.dart` | Sign In / Register tabs |
| `lib/screens/home_screen.dart` | Subject tiles, character cards |
| `lib/screens/chat_screen.dart` | AI chat, voice input, TTS, PIN lock |
| `lib/screens/badges_screen.dart` | Badge grid |
| `lib/screens/settings_screen.dart` | Profile management, PIN change |
| `lib/services/elevenlabs_service.dart` | Voice synthesis (natural AI voice) |

### 8.4 Building for Android

```bash
# Debug APK (for testing)
flutter build apk --release

# Signed APK for Play Store
flutter build apk --release \
  --dart-define=FLAVOR=prod \
  --obfuscate \
  --split-debug-info=build/debug-info
```

The APK is in `build/app/outputs/flutter-apk/app-release.apk`.

### 8.5 Building for iOS

```bash
flutter build ipa --release
```

Requires Apple Developer account ($99/year). The `.ipa` is in `build/ios/ipa/`.

### 8.6 Parental PIN Lock

The mobile app enforces a 4-digit parent PIN before a child can exit the chat screen. This is built into `ChatScreen` via `PopScope`:

- PIN is set by parent on first use
- PIN is stored hashed in `AuthService`
- Wrong PIN triggers a shake animation
- 5 failed attempts locks for 5 minutes
- Parent can reset PIN from Settings screen

This behavior is always on and cannot be disabled in child-facing deployments.

### 8.7 Voice features

```dart
// ElevenLabs TTS (natural voice)
final _elevenLabs = ElevenLabsService();
await _elevenLabs.speak(aiResponse, voiceId: 'your_voice_id');

// Falls back to flutter_tts if ElevenLabs fails or is unconfigured
final _tts = FlutterTts();
await _tts.speak(aiResponse);

// Speech-to-text input
final _stt = SpeechToText();
await _stt.listen(onResult: (result) => setState(() => _input = result.recognizedWords));
```

To use natural voices, create an ElevenLabs account (Starter plan, $5/mo), clone a voice or use a library voice, and set the voice IDs in `lib/services/elevenlabs_service.dart`.

---

## 9. Onboarding Process

### Timeline: 3–5 business days from contract signing

```
Day 1 — Configuration
  ├── You fill in the Tenant Config Form (below)
  ├── We provision your client + client_config rows in Supabase
  ├── We add your domain(s) to ALLOWED_ORIGINS on Railway
  └── We create your admin user account

Day 2 — Delivery
  ├── Web: We hand over the branded HTML/CSS/JS source, or you embed via iframe
  ├── Mobile: We deliver Flutter source code, configured and building
  └── We share API credentials (your admin JWT, test parent account)

Day 3 — Integration & Testing
  ├── Your dev team integrates and tests against the production API
  ├── We're available for questions (Slack or email)
  └── You verify: character names, colors, subjects, lesson plans, badges

Day 4 — Acceptance Testing
  ├── End-to-end test: signup → chat → dashboard → payment
  ├── COPPA review (if serving children under 13)
  └── Load test (if > 500 concurrent users expected)

Day 5 — Go Live
  ├── DNS pointing to your domain
  ├── SSL cert (automatic via Netlify / your CDN)
  └── Monitoring alerts configured
```

### Tenant Config Form

Fill this in and send to iris@threebabybirdies.com:

```
Organization Name:
Primary Domain (e.g. app.yourschool.com):
Admin Email:
Character 1 Name:
Character 1 Personality (1-2 sentences):
Character 2 Name:
Character 2 Personality (1-2 sentences):
Enabled Subjects (circle): spelling / math / rhyming / grammar / puzzles / literature
Primary Brand Color (hex):
Secondary Brand Color (hex):
Forbidden Topics (beyond defaults):
Custom Knowledge Base Facts:
Subscription Tiers Needed: trial / individual / premium / classroom / custom
Stripe Account (for payments): yes — we use yours / no — use platform billing
ElevenLabs Voice IDs (optional):
Target App Stores: Android / iOS / both / web only
Expected Monthly Active Users:
COPPA applicable (serving under-13s): yes / no
```

---

## 10. Data Isolation & Multi-Tenancy

Every record in every table is stamped with `client_id`. The backend enforces this at the query layer — no tenant can ever read another tenant's data, even if they have a valid JWT.

```
TenantSafeQuery (backend/app/db/tenant.py)
  → Every SELECT, INSERT, UPDATE automatically includes WHERE client_id = <your_id>
  → No raw Supabase queries are exposed to API consumers
  → Cross-tenant leakage is architecturally impossible
```

**What is shared across tenants:**
- The Railway compute instance (CPU / RAM)
- The Claude API key (Anthropic billing pooled, costs tracked per tenant via `usage_logs`)
- The Redis instance (keys are namespaced by tenant IP / session)

**What is NOT shared:**
- Database rows (all isolated by `client_id`)
- User accounts (a parent at School A cannot log into School B)
- Chat sessions, progress, badges, lesson plans, usage logs

### Self-Hosted Option

If your organization requires full data sovereignty (e.g., government, healthcare), we can deliver the complete backend source code for self-hosted deployment on your own infrastructure. You would need:

- A server running Python 3.11+ (Railway, AWS, GCP, Azure, or bare metal)
- A PostgreSQL database (Supabase or self-hosted)
- An Anthropic API key
- A Stripe account (for payments)
- A Redis instance

---

## 11. Security & COPPA Compliance

### Security Controls

| Layer | Control |
|---|---|
| **Transport** | HTTPS everywhere, HSTS headers |
| **Authentication** | JWT (HS256), 7-day expiry, bcrypt password hashing |
| **Authorization** | Role-based (parent / teacher / admin), tenant-scoped queries |
| **Input** | 12-pattern prompt injection scanner, control character stripping, 500-char length cap |
| **AI pipeline** | System prompt constraints (subject lock, forbidden topic enforcement) |
| **Output** | Post-generation content safety scan before response is returned |
| **Rate limiting** | 15 req/min (chat), 10 req/min (demo), 4 demo msg/IP/hour (Redis) |
| **Headers** | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `HSTS` |
| **Error handling** | Global exception handler — stack traces never exposed to clients |
| **Frontend** | All API responses HTML-escaped before DOM injection — no XSS surface |

### COPPA Compliance

The platform is designed for children under 13. Key compliance controls:

- **Children never register** — only parents or teachers create accounts
- **No PII collected from children** — profiles contain only nickname, age (optional), grade (optional)
- **No advertising tracking** — no third-party pixels, no behavioral profiling
- **No real names** — child profiles use nicknames only, not legal names
- **No contact info** — no email, phone, or address collected for children
- **Chat is for response generation only** — messages are not stored for advertising or sold
- **Parent right to delete** — email request to iris@threebabybirdies.com → deletion within 30 days
- **Parental controls** — 4-digit PIN locks out child from dashboard, settings, and logout
- **Data minimization** — only data necessary for the educational service is collected

If your organization serves children in the EU, GDPR Article 8 also applies (parental consent for under-16s depending on member state). We can provide a DPIA (Data Protection Impact Assessment) on request.

---

## 12. Subscription Tiers & Pricing

### White-Label Licensing Fee (paid to Three Baby Birdies)

| Tier | Per-Month Fee | Includes |
|---|---|---|
| **Starter** | Contact us | Up to 200 MAU, shared infrastructure |
| **Growth** | Contact us | Up to 2,000 MAU, priority support |
| **Enterprise** | Contact us | Unlimited MAU, dedicated Railway instance, SLA |
| **Self-Hosted** | One-time fee | Full source delivery, you pay infra costs |

### End-User Subscription Tiers (you collect via Stripe)

These are the tiers your end-users pay. You set the prices; we enforce the limits.

| Plan | Default Limit | Suggested Price |
|---|---|---|
| Free Trial | 100 messages/mo, 3 months | $0 |
| Individual | 400 messages/mo | $9.99/mo |
| Premium | 1,000 messages/mo | $19.99/mo |
| Classroom | 200 msg/student, up to 30 | $29.99/mo |

You connect your own Stripe account. Payments go directly to you. We do not take a revenue share on end-user subscriptions.

### Estimated Infrastructure Costs (if self-hosted)

| Service | Monthly |
|---|---|
| Railway Hobby (backend) | $5 + ~$2–5 usage |
| Supabase Pro (database) | $25 |
| Anthropic Claude API | ~$10–30 (0–50 users) / ~$100–200 (500+ users) |
| ElevenLabs Starter (voice) | $5 |
| Redis | $0 (Railway plugin, ~$0–3 usage) |
| Netlify (website) | $0 (free tier) |
| **Total (small scale)** | **~$50–70/mo** |

---

## 13. SLA & Support

### Uptime
- **Target:** 99.9% monthly uptime on Railway Hobby plan
- **Anthropic API:** Subject to Anthropic's own SLA; circuit breaker pattern ensures graceful degradation (safe fallback response if Claude is unreachable)
- **Monitoring:** Sentry error tracking (configurable DSN per tenant)

### Support Channels
- **Email:** iris@threebabybirdies.com
- **Response time:** 24 hours (Starter), 4 hours (Growth), 1 hour (Enterprise)
- **Slack:** Dedicated channel available for Growth and Enterprise

### What We Handle
- API updates and new features
- Security patches (applied within 24 hours of discovery)
- Anthropic model upgrades (we track deprecations and migrate proactively)
- Supabase schema migrations
- Railway infrastructure monitoring

### What You Handle
- Your frontend code (unless we delivered it)
- Your Stripe account and pricing configuration
- Your ElevenLabs voice clones
- App Store submissions for your brand
- Your domain DNS and SSL (Netlify handles SSL automatically)

---

## 14. FAQ

**Q: Do my users need to know this is powered by Chirpy's Classroom or Three Baby Birdies?**  
No. Your users see only your brand. "Three Baby Birdies" and "Chirpy" are not exposed anywhere in the API responses or mobile app unless your `client_config` explicitly includes them.

**Q: Can we add our own subjects beyond the 6 built-in ones?**  
Yes. Custom subjects require a development engagement (typically 1–3 days). We write the subject-specific AI instructions and add them to `prompt_builder.py`. Contact us with your curriculum requirements.

**Q: Can we connect our own LMS (Canvas, Schoology, Google Classroom) for single sign-on?**  
SSO via OAuth 2.0 / SAML is available as a custom integration. The platform currently supports JWT-based auth natively; SSO bridges can be built in front of the API.

**Q: What happens if Anthropic's Claude API goes down?**  
The circuit breaker pattern (`app/services/circuit_breaker.py`) intercepts failures and returns a safe, in-character fallback message instead of an error. Users see "I need a tiny rest — try again in a moment!" rather than a crash. The circuit breaker auto-recovers when Claude comes back online.

**Q: Can we use a different AI model (GPT-4, Gemini, etc.)?**  
The platform is designed for Claude. Migrating to a different model requires changes to `claude_service.py` and testing of all prompt behaviors. This is a paid engagement.

**Q: How do we handle parents who want their data deleted?**  
Direct them to email iris@threebabybirdies.com (or your own support email). We delete all records for the user and all associated child profiles within 30 days, in compliance with COPPA. We can also provide a self-service deletion endpoint on request.

**Q: Is there a staging environment for testing?**  
We can provision a separate Railway deployment pointing to a staging Supabase instance. Recommended for Enterprise customers before pushing changes to production.

**Q: What's the maximum message length a user can send?**  
500 characters, enforced by Pydantic validation and the input sanitizer. This is intentional — the platform is designed for short educational exchanges, not essay submission.

**Q: Can we see per-tenant usage costs so we can bill clients?**  
Yes. The `usage_logs` table records `input_tokens`, `output_tokens`, and `cost_usd` per API call, stamped with `client_id`, `user_id`, and `child_profile_id`. The `/admin/usage` endpoint exposes this as a daily breakdown table.

**Q: Do you support voice input on the web (not just mobile)?**  
The Web Speech API (`webkitSpeechRecognition`) is available in Chrome and Edge. We can add it to the web frontend on request. Safari requires a workaround. The mobile app uses `speech_to_text` (Flutter plugin) which works on both iOS and Android.

---

*For integration support, custom development quotes, or to schedule a technical walkthrough with the TechManhattan team, contact:*  
**iris@threebabybirdies.com**

*Last updated: June 2026*
