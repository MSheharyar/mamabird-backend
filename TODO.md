# MamaBird & Chirpy — TODO & Backlog

> Last updated: June 24, 2026  
> Legend: 🔴 Urgent · 🟡 Important · 🟢 Nice to have · ⏳ Blocked on client

---

## 🔴 Urgent (Do Before Launch)

- [ ] **Upgrade Railway to Hobby plan** — trial expires in ~29 days. Backend goes offline without it. ($5/mo)
- [ ] **Content safety test log** — run 10 test prompts against Railway, document pass/fail in `backend/tests/content_safety_log.md`
- [ ] **Set `EBOOK_PDF_URL` env var on Railway** — Iris must upload the PDF to Supabase Storage or Google Drive and share the URL ⏳

---

## 🔴 Security — Missing (from audit)

- [ ] **Add 3 missing HTTP security headers** in `gateway_middleware` (`main.py`):
  ```python
  response.headers["Content-Security-Policy"] = "default-src 'none'"
  response.headers["Referrer-Policy"] = "no-referrer"
  response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
  ```
- [ ] **API versioning** — add `/v1/` prefix to all routers before user base grows. Easy now, painful later.
- [ ] **Dependency update process** — add GitHub Dependabot config (`.github/dependabot.yml`) to get automated PRs for vulnerable packages. Keep bcrypt pinned at 3.2.2.

---

## 🟡 Security — Partial (from audit)

- [ ] **Output sanitization** — AI responses returned raw. Strip or escape any `<script>` tags from Claude's output before sending to client.
- [ ] **Security event logging** — log failed login attempts, injection detections, and lockout events to a `security_events` table (not just `usage_logs`).
- [ ] **Suppress Pydantic 422 field detail** — override the 422 validation error handler so it returns a generic message instead of leaking field names/schema:
  ```python
  @app.exception_handler(RequestValidationError)
  async def validation_handler(request, exc):
      return JSONResponse(status_code=422, content={"detail": "Invalid request data"})
  ```
- [ ] **Penetration test / OWASP ZAP scan** — run at least a basic automated scan against the staging Railway URL before App Store submission.

---

## 🟡 Client Blockers — Waiting on Iris ⏳

- [ ] **Stripe live keys** — Iris must log into stripe.com and provide:
  - `STRIPE_SECRET_KEY=sk_live_...`
  - `STRIPE_WEBHOOK_SECRET=whsec_...`
  - `STRIPE_PRICE_ID_INDIVIDUAL=price_...`
  - `STRIPE_PRICE_ID_PREMIUM=price_...`
  - `STRIPE_PRICE_ID_CLASSROOM=price_...`
- [ ] **ElevenLabs voice** — Iris/dev must either:
  - Create a free Instant Voice Clone for Mama Bird, OR
  - Upgrade ElevenLabs to Starter ($5/mo) to unlock Lauren library voice
  - Then update `_mamaBirdVoice` / `_chirpyVoice` in `lib/services/elevenlabs_service.dart`

---

## 🟡 Mobile App — Remaining

- [ ] **Google Play submission** — build release APK, create Play Store listing, upload screenshots, submit for review
- [ ] **Apple App Store submission** — requires $99/yr Apple Developer account. Build IPA, submit via App Store Connect.
- [ ] **App icon** — replace default Flutter icon with Three Baby Birdies brand icon (🐦 on red background)
- [ ] **Splash screen native** — configure Android/iOS native splash (currently only Flutter-level splash)
- [ ] **Push notifications** — badge earned, streak reminder (Firebase Cloud Messaging)
- [ ] **In-app subscription management** — let users cancel subscription without emailing (Stripe Customer Portal)

---

## 🟡 Backend — Remaining

- [ ] **Iris admin runbook** — write a Google Doc / PDF explaining how to use the admin dashboard, check usage, manage users
- [ ] **Stripe webhook test** — verify all 4 webhook events work correctly with live keys once Iris provides them
- [ ] **`grace` vs `grace_period` audit** — confirm all webhook handlers write `"grace"` not `"grace_period"` in `dependencies.py`
- [ ] **Token refresh endpoint** — currently tokens expire after 24h and user is logged out. Add `POST /auth/refresh` to silently renew tokens.
- [ ] **Password reset flow** — no forgot-password endpoint exists yet. Add `POST /auth/forgot-password` + email link.

---

## 🟢 Website — Nice to Have

- [ ] **Blog posts** — `blog.html` is a placeholder. Write 3–5 real articles about children's reading and phonics.
- [ ] **Contact form backend** — `contact.html` has a form but no submission endpoint. Wire to Resend/SendGrid or Formspree.
- [ ] **SEO meta tags** — add `<meta name="description">`, Open Graph tags, and structured data to all pages for Google ranking.
- [ ] **Cookie consent banner** — GDPR best practice even though the site uses minimal cookies.
- [ ] **Sitemap.xml + robots.txt** — for Google indexing.

---

## 🟢 Future Features (Post-MVP)

- [ ] **Teacher classroom dashboard** — grid view of all students' progress, subject heatmap, weekly report PDF
- [ ] **Offline mode** — cache last 5 chat sessions in Flutter app for use without internet
- [ ] **Multi-language support** — Spanish first (large market for Iris's target audience)
- [ ] **Spline 3D animations** — replace CSS blob animations on homepage with Spline embeds (Iris shared a Spline file)
- [ ] **Lesson plan sharing** — parents can share generated lesson plans via link or email
- [ ] **Streak system** — track daily login streaks, reward with badges (data structure already exists)
- [ ] **Parent weekly email digest** — what their child learned this week, badges earned, suggested next session
- [ ] **White-label second client** — the multi-tenant architecture supports it. Find a second edtech client to license the platform.

---

## ✅ Completed (reference)

- [x] FastAPI backend — auth, chat, profiles, badges, sessions, dashboard, admin, payments
- [x] Multi-tenant white-label architecture
- [x] Circuit breaker + rate limiting + content safety pipeline
- [x] Stripe subscription checkout (3 tiers) + eBook one-time purchase
- [x] Flutter app — all screens with KidZo-style UI redesign
- [x] Parent PIN lock (numpad, shake animation)
- [x] ElevenLabs TTS integration (with flutter_tts fallback)
- [x] Website — 13 pages including Privacy Policy, Terms, COPPA
- [x] 3 GitHub repos with auto-deploy pipelines (Railway + Netlify)
- [x] `flutter analyze` — 0 issues
- [x] Security headers (X-Frame-Options, X-Content-Type-Options, XSS, HSTS)
- [x] Login brute-force lockout (5 attempts → 300s lock)
- [x] Token revocation via `token_version`
- [x] Docs endpoint disabled by default (`ENABLE_DOCS=false`)
