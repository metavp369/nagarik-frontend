# Nagarik Changelog



## 2026-03-10 — Public Safety Dashboard

### Route: `/safety-dashboard` (public, no auth)
### Sections:
1. **Top Metrics Bar** — 6 cards: Active Sessions, Signals, AI Predictions, Alerts, Cities, Avg Response
2. **Live Incident Map** — SVG city nodes with pulsing risk indicators, 6 cities
3. **City Zone Grid** — 6 zones with risk levels (HIGH/ELEVATED/MODERATE/LOW), session counts, signal counts
4. **Active Incidents Panel** — Real incidents from DB: type, severity (critical/high/medium/low), status, zone, timestamp, response time
5. **Intelligence Feed** — 10 real-time events with color-coded types
6. **AI Risk Intelligence** — 4 metric boxes (High Risk, Anomalies, Predictions, Unresolved) + Risk Zones + AI Recommendations (priority-coded)
7. **Response Actions** — 3 demo buttons (Dispatch Security, Notify Guardian, Activate Safety Protocol) with local action log
8. **Incident Replay** — Link to /telemetry

### Backend APIs (NEW)
- `GET /api/status/incidents` — 15 real anonymized incidents from PostgreSQL (incidents + sos_logs)
- `GET /api/status/risk-intelligence` — Aggregated risk analysis: high-risk counts, anomaly clusters, AI predictions, risk zones, recommendations

### Testing
- Backend: 16/16 passed (100%)
- Frontend: 100% — all 17 features verified
- Test report: `/app/test_reports/iteration_133.json`


## 2026-03-09 — City Safety Simulation

### Component: `/app/frontend/src/components/CitySafetySimulation.jsx`
- 5-step animated simulation: Monitoring → Anomaly Detected → Alert Propagation → AI Response → Resolved
- 12 city nodes: schools, universities, transit hubs, public zones (SVG-based grid)
- 20 connecting edges with animated color transitions
- Color-coded states: green(safe), orange(warning), red(alert), cyan(responding)
- Status badges per step (MONITORING/ANOMALY/ALERT/RESPONDING/RESOLVED)
- Progress bar, step counter, descriptive message panel
- "Run City Safety Simulation" start button → "Replay Simulation" on completion
- Total runtime: ~22 seconds (auto-advancing steps)
- Placed on homepage between Live Threat Intelligence and City Safety Operations
- Chatbot recognizes "city simulation" keywords → links to homepage

### Testing
- Frontend: 100% — all 5 steps, 12 nodes, badges, progress bar, replay
- Backend: 100% — chatbot keyword triggers
- Test report: `/app/test_reports/iteration_132.json`


## 2026-03-09 — AI Chatbot (Ask Nagarik AI)

### Features
- Floating "Ask Nagarik AI" button on all marketing pages (/, /investors, /pilot, /telemetry)
- GPT-5.2 powered responses via Emergent LLM Key with comprehensive system prompt
- 7 quick action buttons: About, School Safety, Corporate Safety, Pilot Deployment, Investor Info, Run Live Safety Demo, Contact Support
- **Live Safety Demo**: 11-step simulated scenario (detection → anomaly → alert → guardian response → resolution) with color-coded messages (cyan/amber/red/green), ~22 second runtime
- **Lead Capture**: In-chat form (name, institution, email, city) → stores in pilot_leads + SendGrid email to partners@Nagarik.app & hello@Nagarik.app
- Page linking: chatbot suggests /pilot, /telemetry, /investors based on context
- Rate limited: 30 messages/min, 10 leads/hour

### Backend
- `POST /api/chatbot/message` — keyword routing: demo trigger, lead prompt, or GPT-5.2 response
- `GET /api/chatbot/demo-steps` — returns 11 demo steps with timing
- `POST /api/chatbot/lead` — stores lead in pilot_leads table

### Testing
- Backend: 12/12 passed (100%) — GPT-5.2 responses, demo trigger, lead capture
- Frontend: 100% — all UI features verified
- Test report: `/app/test_reports/iteration_131.json`


## 2026-03-09 — Real Telemetry Data + WhatsApp Support Button

### Real Telemetry Connection
- `/api/status/platform` now queries PostgreSQL: safety_events, telemetries, incidents, guardian_alerts, behavior_anomalies, guardian_ai_predictions, users
- `/api/status/events` builds anonymized feed from: safety_events, incidents, behavior_anomalies, sos_logs (20 events, zone-anonymized)
- `/api/status/metrics` queries real totals: pilot_leads, guardian_relationships, safety_events, incidents, users, sos_logs, telemetries
- 30-second in-memory cache prevents DB overload
- Graceful fallback to demo data if DB queries fail
- No sensitive data exposed (no user IDs, coordinates, names)

### WhatsApp Support Button
- Floating green FAB (bottom-right) on marketing pages only (/, /investors, /pilot, /telemetry)
- Hidden on app pages (/login, /family, /m/*)
- Click opens tooltip with "Chat with us" and "Open WhatsApp" link (wa.me)
- Component: `/app/frontend/src/components/WhatsAppButton.jsx`

### Testing
- Backend: 20/20 passed (100%) — real data verification, caching, anonymization
- Frontend: 100% — all sections render, WhatsApp button visible/hidden correctly
- Test report: `/app/test_reports/iteration_130.json`


## 2026-03-09 — API Rate Limiting & Security Headers

### Rate Limiting (slowapi + SlowAPIMiddleware)
- **Auth endpoints** (`/api/auth/login`, `/api/auth/register`, `/api/auth/google`, `/api/auth/google/code`): **5 requests/minute** per IP
- **Telemetry endpoints** (`/api/status/platform`, `/api/status/events`, `/api/status/metrics`): **60 requests/minute** per IP
- **Pilot signup** (`/api/pilot/signup`): **10 requests/hour** per IP
- **SOS trigger** (`/api/sos/trigger`): **10 requests/minute** per IP
- Returns HTTP 429 `{"error": "Too many requests. Please try again later."}`

### Security Headers (SecurityHeadersMiddleware)
- `X-Frame-Options: DENY` — prevents clickjacking
- `X-Content-Type-Options: nosniff` — prevents MIME sniffing
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` — enforces HTTPS
- `Referrer-Policy: strict-origin-when-cross-origin` — controls referrer info
- `X-XSS-Protection: 1; mode=block` — XSS filter
- `Permissions-Policy: camera=(), microphone=(), geolocation=(self)` — feature policy

### Files
- `/app/backend/app/core/rate_limiter.py` — shared limiter instance
- `/app/backend/app/core/security_headers.py` — SecurityHeadersMiddleware

### Testing
- Backend: 14/14 tests passed (100%) — rate limits verified, security headers verified
- Frontend: 4/4 pages load correctly
- Test report: `/app/test_reports/iteration_129.json`


## 2026-03-09 — Live Telemetry Dashboard

### Route: `/telemetry`
- Hero with "Nagarik Live Safety Network" heading, "LIVE TELEMETRY" badge, auto-refresh indicator
- Nav bar: "ALL SYSTEMS OPERATIONAL" status with green pulsing dot
- Platform Status: 6 animated counter cards (Active Sessions, Signals Today, AI Predictions, Alerts Triggered, Cities Monitored, Avg Response Time)
- Live Intelligence Feed: 20 scrolling events with color coding (anomaly=orange, alert=red, system=cyan, resolved=green)
- City Safety Heatmap: 6 cities (Mumbai, Delhi, Bangalore, Pune, Dubai, London) with risk levels, active sessions, and pulsing indicators
- System Health: 8 modules (AI Safety Brain, Command Center, Guardian Network, etc.) all showing "operational" with >99% uptime
- Network Growth: Institutions Protected (14), Active Guardians (342), Total Safety Sessions (48,720), Incidents Resolved (1,847)
- Safety Network Map: 6 city nodes with staggered pulsing animation on grid background
- Auto-refreshes every 8 seconds via polling

### Backend APIs
- `GET /api/status/platform` — returns operational status, metrics, cities, system health
- `GET /api/status/events` — returns 20 anonymized intelligence feed events
- `GET /api/status/metrics` — returns network growth totals

### Note
- `/status` URL intercepted by Kubernetes health check; using `/telemetry` instead
- All data is demo/simulated (intentional for investor demos)

### Testing
- Backend: 12/12 tests passed (100%)
- Frontend: 100% — all 6 sections, navigation, design verified
- Test report: `/app/test_reports/iteration_128.json`

## 2026-03-09 — Marketing Website for Nagarik.care

### Homepage (`/`)
- Hero with "AI Safety Infrastructure" heading, animated grid background, pulsing status badge
- Live Intelligence Ticker: 14 rotating events (2.2s cycle) with color-coded severity (critical/alert/warning/success/info)
- Trusted Environments: Schools, Universities, Corporate Campuses, Smart Cities, Public Safety
- Live Threat Intelligence: 6 real-time signal metrics with delta indicators
- City Safety Operations: 6 zone cards with risk levels and active session counts
- Platform Architecture: 4-step pipeline (User App → AI Safety Brain → Command Center → City Intelligence)
- Safety Network Effect: Individual/Institutional/City layer cards
- CTA: "Request Pilot Deployment" (/pilot), "Schedule Demo" (mailto)
- Footer with 5 contact emails grouped by category + nav links

### Investor Page (`/investors`)
- 7 sections: Vision, Platform Metrics (animated counters), Architecture Pipeline, Technology Stack (8 AI engines), Market Opportunity ($44.7B TAM, 5 sectors), Pilot Deployments, Founder Vision
- Consistent dark Enterprise/Deep-Tech design

### Pilot Signup Page (`/pilot`)
- Lead capture form: institution name, contact, email, phone, city, institution type, headcount, message
- Backend: `POST /api/pilot/signup` stores in `pilot_leads` table + SendGrid email to partners@Nagarik.app & hello@Nagarik.app
- Success state with "Thank You" message and 48-hour response SLA
- Admin endpoint: `GET /api/pilot/leads`

### Routing
- `/` → NagarikHomePage (public), `/investors` → InvestorPage (public), `/pilot` → PilotSignupPage (public)
- All existing protected routes (/family, /login, /m/*) preserved

### Testing
- Backend: 9/9 tests passed (100%) — pilot signup, validation, data persistence
- Frontend: 100% — all sections, navigation, form submission, design verification
- Test report: `/app/test_reports/iteration_127.json`


## 2026-03-09 — Demo Mode + Guardian Live Map + Incident Replay + Firebase Push

### Demo Mode (Sales Weapon)
- **30-second simulation**: Session Start → Risk Increase → Anomaly → Route Deviation → SOS → Guardian Alert → Command Center Escalation → Incident Replay
- **3 demo users**: Riya Sharma, Ananya Patel, Neha Verma with auto-created guardian relationships
- **Command Center integration**: DEMO toggle button in header with live status bar showing step progress
- **Full data pipeline**: Creates real sessions, alerts, SOS events, and push notifications
- API: `POST /api/demo/start`, `POST /api/demo/stop`, `GET /api/demo/status`
- Testing: 100% — `/app/test_reports/iteration_126.json`

### Guardian Live Map (`/m/guardian-live-map`)
- Dark Leaflet map, risk-colored user marker, multi-user selector pills
- User info card with risk level, session metrics (duration/distance/speed)
- Bottom AI intelligence panel + 4 action buttons (Call, Message, Safety Ping, Alert)
- Auto-refresh every 10s, route polyline, risk zone overlays

### Incident Replay (`/m/incidents`)
- Incident list grouped by date with severity badges
- Timeline replay: session start → alert events → session end
- AI Analysis panel: root cause, response time, preventable flag, contributing factors

### Firebase Push Notifications (FCM LIVE)
- Firebase Admin SDK operational, multi-channel escalation rules
- SOS (Push+Email), Risk (Push), Invites (Email+Push), Sessions (Push)
- `/m/notifications` page with push status and history

### APIs Added
- `POST /api/demo/start|stop`, `GET /api/demo/status`
- `GET /api/guardian/live/protected-users|status/{id}`
- `GET /api/guardian/incidents|{id}/replay`
- `POST /api/device/register`, `GET /api/device/push-status|notifications`


## 2026-03-09 — P1: Guardian Live Map + Incident Replay Mobile


## 2026-03-09 — Mobile PWA Sprint 1 MVP (8 Screens)

### Mobile App Routes (under `/m/*`)
All 8 screens implemented within existing React frontend as PWA layer:

**1. Mobile Home** (`/m/home`)
- Risk score card with AI assessment and risk level badge
- Threat assessment card (when available)
- Session status with Start/View toggle
- Quick actions grid: Safe Route, Fake Call, Guardians, Alerts
- Last alert card, Guardian network summary
- Powered by single API: `GET /api/safety-events/user-dashboard`

**2. Start Session** (`/m/session`)
- Destination name input, Lat/Lng fields
- Travel mode selector: Walk, Drive, Transit
- Auto-redirect to Live screen if session already active
- Calls: `POST /api/safety-events/start-session`

**3. Live Session** (`/m/live`)
- Large risk gauge with real-time score and level badge
- Elapsed timer, distance, updates, alerts stats
- Current location display with accuracy
- Route deviation warning when detected
- Geolocation watchPosition for continuous location sharing
- End session button
- Calls: `GET /api/safety-events/session-status`, `POST /api/safety-events/share-location`

**4. Safe Route Analysis** (`/m/safe-route`)
- Origin/Destination coordinate inputs
- "Use My Location" button with geolocation
- Route cards with safety scores, distance, duration, factor breakdowns
- Recommended route badge
- Calls: `POST /api/safety-events/safe-route`

**5. Emergency SOS** (`/m/sos`)
- Press-and-hold 3-second trigger with circular progress
- Countdown animation with haptic feedback
- Guardian notification list after SOS sent
- Retry on failure, Done button to reset
- Fake Call shortcut
- Calls: `POST /api/safety-events/sos`

**6. Fake Call** (`/m/fake-call`)
- 5 caller presets (Mom, Dad, Boss, Partner, Friend)
- Custom name input, delay slider (0-30s)
- Full-screen ringing/answered phases
- Accept/Decline buttons, hangup
- Calls: `POST /api/safety-events/fake-call`

**7. Alerts** (`/m/alerts`)
- Alert list with severity badges and icons
- Time ago timestamps, location display
- Recommendations when available
- Empty state when no alerts
- Auto-refresh every 15 seconds
- Calls: `GET /api/safety-events/guardian-alerts`

**8. Profile** (`/m/profile`)
- User card with email, role badge
- Guardian network: guardians list, emergency contacts count
- Individual guardian cards with primary badge
- Settings: Notifications, Privacy, SOS Configuration
- Sign Out button
- Calls: `GET /api/guardian-network/`, `GET /api/guardian-network/emergency-contacts`

### Shared Components
- **MobileLayout** — 430px max-width container, tab bar (Home, Map, SOS, Alerts, Profile), SOS as centered red button
- **FloatingSafetyIndicator** — Top bar showing risk level + score, expandable for threat details, hidden on SOS/Live/FakeCall screens

### Shake-to-SOS Feature
- **useShakeDetector hook**: DeviceMotion API shake detection with configurable threshold/cooldown
- **ShakeSOSOverlay**: Full-screen 3-second countdown with cancel, sending, sent, and failed phases
- **MobileLayout integration**: Overlay rendered globally on all mobile screens
- **Profile toggle**: Enable/disable in Emergency Controls section, persisted in localStorage
- **Backend**: `POST /api/safety-events/sos` accepts `trigger_type='shake'` with location
- Testing: Backend 5/5, Frontend 9/9 — `/app/test_reports/iteration_120.json`

### PWA Installability
- **manifest.json**: name "Nagarik", start_url "/m/home", display "standalone", icons 192x192 & 512x512
- **Service worker** (sw.js): Cache-first for static, network-first for API, push notification handler
- **Apple meta tags**: apple-mobile-web-app-capable, apple-touch-icon, theme-color
- **InstallPrompt component**: "Add to home screen" banner

### Guardian Management UI
- `/m/guardians` — Guardian list with escalation order, primary badge, set-primary, remove
- `/m/add-guardian` — Two modes: Create Invite Link (primary) or Add Directly. Email, name, 6 relationship types
- `/m/contacts` — Emergency contacts CRUD with inline form

### Guardian Invite Links — Growth Engine
- 5 API endpoints: `POST /invite`, `GET /invite/{token}` (public), `GET /invites`, `POST /invite/{token}/accept`, `DELETE /invite/{token}`
- `guardian_invites` table with 48h token expiry, status tracking
- Public landing page at `/invite/:token` — personalized with inviter name, relationship, benefits
- Auth flow: unauthenticated → login → auto-redirect → accept → relationship created
- Share button (Web Share API) + Copy Link + share message preview
- Security: 48h expiry, self-invite prevention, duplicate handling, revocation
- Testing: Backend 15/15, Frontend all verified — `/app/test_reports/iteration_122.json`

### Push Notification Infrastructure
- **NotificationService**: Centralized dispatcher (SOS, risk, guardian, session alerts)
- **Wired into SOS handler**: Push + email dispatched to all guardians on SOS
- **Device registration**: `POST /api/device/register`, `GET /api/device/notifications`
- **Tables**: `push_notifications` (history), `device_tokens` (registered devices)
- FCM delivery **stored but not pushed** (awaiting Firebase credentials)

### Email Invite Delivery
- **SendGrid integration**: `email_service.py` with dark-themed HTML templates
- **Guardian invite email**: Accept button, features, 48h expiry
- **SOS alert email**: Emergency-styled to all guardians
- **Graceful degradation**: `email_sent=false` when SENDGRID_API_KEY not set

### AI Insights Screen (`/m/ai`)
- Risk gauge with score/10, risk level badge
- 5 category bars (Behavior, Location, Device, Environment, Response)
- Top risk factors with impact scores
- Threat assessment narrative from GPT-5.2
- AI recommendation, safety trend chart
- Testing: Backend 13/13, Frontend all verified — `/app/test_reports/iteration_123.json`


### 3 Mobile Foundations (Pre-Mobile App Architecture)
**1. Guardian Network Model** — `GuardianRelationship` + `EmergencyContact` models, 7 CRUD APIs, escalation chain, soft delete, priority ordering
**2. Safety Event API** — 9 mobile-ready endpoints at `/api/safety-events/` (SOS, sessions, risk, route, alerts, location, fake-call), with rate limiting
**3. Real-Time Event System** — WebSocket gateway `/api/ws/events`, event pipeline (emit_sos/location/risk/incident/session_alert), push-to-guardian-network
- Test: `/app/test_reports/iteration_118.json` — 40/40 passed

### P0 Bug Fix: Guardian AI Risk Panel
- **Root Cause**: Incidents had `senior_id` (FK to seniors table) but Guardian AI API requires `user_id` (FK to users table). The mapping is `seniors.guardian_id` → `user_id`.
- **Backend Fix**: Added `user_id` (from `Senior.guardian_id`) to incident API responses in both `GET /api/operator/incidents` and `GET /api/operator/command-center` (active_incidents).
- **Frontend Fix**: Updated DispatchPanel in Operator Dashboard to use `incident.user_id || incident.senior_id` for AI API calls.
- Test reports: `/app/test_reports/iteration_114.json` — 13/13 tests passed

### P1: AI Replay Analysis
- **Backend**: New endpoint `GET /api/replay/{session_id}/analysis` — risk peaks, response times, preventable moments, recommendations
- **Frontend**: `AIAnalysisPanel` overlay in Journey Replay — auto-opens when playback ends + manual "AI Analysis" button
- Test reports: `/app/test_reports/iteration_115.json` — 16/16 backend + all frontend tests passed

### 5 Palantir-Grade Command Center Intelligence Features
All with **"Powered by Guardian AI Engine"** branding.

**1. City Risk Radar** (Map overlay, top-left)
- Glass-morphism panel showing critical/high-risk/rising zone counts
- Top escalating area with risk score
- Uses existing heatmap data

**2. Predictive Alert Bar** (Map overlay, bottom-left)
- Behavior anomaly %, location risk %, environmental factor %
- Overall forecast level (LOW/MEDIUM/HIGH/CRITICAL) with color-coded badge
- Progress bars for each probability

**3. AI Reasoning Panel** (Bottom panel)
- Risk score display with confidence percentage
- 5-factor breakdown bars: Behavioral Pattern, Location Intelligence, Device Reliability, Environmental Risk, Response Readiness
- Factor descriptions explaining why AI flagged the user

**4. Digital Twin Profile** (Bottom panel)
- Normal travel hours, typical commute pattern
- Safe zones visited %, avg daily distance
- Current behavior status (NORMAL/SLIGHT DEVIATION/UNUSUAL) with deviation % bar

**5. AI Timeline** (Right sidebar)
- Chronological vertical timeline of risk events
- Color-coded dots (red=alert, orange=rising, amber=anomaly, green=resolved)
- Timestamps and risk scores for each event
- Combines risk history + incident data

**Architecture Changes:**
- Command Center bottom row expanded from 3 to 3 panels: AI Risk Intelligence (with click-to-select) | AI Reasoning | Digital Twin
- Right sidebar: Incident Feed (top) + AI Timeline (bottom)
- Map overlays: City Risk Radar (top-left) + Predictive Alert Bar (bottom-left)
- Auto-select first high-risk user on page load → all panels populate
- Click different user → Reasoning + Twin + Timeline update in real-time
- New component files: `CityRiskRadar.jsx`, `PredictiveAlertBar.jsx`, `AIReasoningPanel.jsx`, `DigitalTwinPanel.jsx`, `AITimeline.jsx`
**6. Threat Assessment Summary** (Map overlay, top-right)
- Threat Level badge with color-coded indicator (SAFE/MODERATE/HIGH/CRITICAL)
- GPT-5.2 powered AI-generated operational safety briefing (2-3 sentences)
- Structured stats: zones escalating, users with anomalies, recent incidents
- Recommended action based on threat level
- Auto-refreshes every 90 seconds with cinematic typing animation
- 60-second cache to avoid excessive API calls
- Fallback template narrative if GPT unavailable
- **Backend:** `GET /api/guardian-ai/insights/threat-assessment`
  - Gathers signals from heatmap cache, high-risk users, recent incidents
  - Calls GPT-5.2 via Emergent LLM Key with structured prompt
  - Returns: threat_level, summary, zones_escalating, users_anomaly, top_zone, recent_incidents, recommended_action, generated_at
- Test reports: `/app/test_reports/iteration_117.json` — 13/13 backend + all frontend tests passed


## 2026-03-08 — Operator Dashboard & Caregiver Dashboard (Tested & Verified)

### Operator Dashboard (`/operator-dashboard`)
- **Incident Dispatch Panel**: Real-time incident queue with severity badges, status filters (all/critical/open/assigned/resolved)
- **Live Map**: Leaflet map with incident markers (SOS=red, alerts=amber) and caregiver positions (green)
- **Dispatch Actions**: Select incident → assign caregiver, resolve, or escalate
- **Active Caregivers Panel**: Shows all caregivers with status (available/busy/offline)
- **Incident Timeline**: Chronological event history for selected incident
- **Quick Actions**: Navigation links to Command Center, Admin Panel, Dashboard
- **Auto-refresh**: Every 15 seconds

### Caregiver Dashboard (`/caregiver`)
- **Profile & Status**: Header shows caregiver name, alert count, visits count, status dropdown
- **Assigned Users**: List of seniors with risk badges, age, active incidents count, last visit date
- **Active Alerts**: Assigned incidents with acknowledge, start, resolve buttons
- **Visit Log**: Create and view visit records for seniors
- **Health Notes**: Create observation notes with severity classification
- **Auto-refresh**: Every 20 seconds

### Backend Additions
- `GET /api/operator/dashboard/metrics` — Incident & caregiver summary metrics
- `GET /api/operator/dashboard/caregivers` — Caregiver list with status
- `GET /api/operator/incidents` — Enriched incident list with senior_name, device_identifier
- `POST /api/operator/incidents/{id}/assign?caregiver_id={id}` — Assign caregiver
- `PATCH /api/operator/incidents/{id}/status?new_status={status}` — Update status
- `POST /api/operator/incidents/{id}/escalate` — Manual escalation
- `GET /api/caregiver/profile` — Caregiver profile with status
- `PATCH /api/caregiver/status` — Update availability
- `GET /api/caregiver/assigned-users` — Assigned seniors list
- `GET /api/caregiver/alerts` — Assigned incidents
- `PATCH /api/caregiver/alerts/{id}/acknowledge` — Acknowledge alert
- `PATCH /api/caregiver/alerts/{id}/status` — Update alert status
- `POST /api/caregiver/visits` — Create visit log
- `POST /api/caregiver/notes` — Create health note
- RBAC enforced: caregiver→operator=403, operator→caregiver=403, unauth=401

### Testing
- Backend: 31/31 pytest tests passed (100%)
- Frontend: All UI elements verified via Playwright
- RBAC: Full role isolation confirmed
- Test report: `/app/test_reports/iteration_109.json`
- Test users: operator1@Nagarik.com, caregiver1@Nagarik.com (password: secret123)

### Real-Time Alert System (2026-03-08)
- **Audio Alert**: Two-tone emergency beep (`/sounds/alert.wav`) plays on new critical incidents
- **Red Flash Animation**: Header flashes red 4x via CSS keyframes (`headerAlertFlash`)
- **Browser Notification**: Native OS notification popup with incident details
- **"NEW CRITICAL" Badge**: Pulsing red badge in header showing count of new critical incidents
- **Auto Camera Focus**: Map auto-flies to incident location (zoom 15) using `MapFlyTo` component
- **Mute/Unmute Toggle**: Volume button in header to silence audio alerts
- **Visual Highlighting**: New incidents get a red ring border + ping animation in the queue (clears after 8s)
- **Pulsing Map Markers**: New critical incidents display 28px markers with dual glow + `newIncidentPulse` animation
- **Auto-Select Incident**: New critical incident auto-selected → dispatch panel opens instantly
- **Command Center Alerts**: Same alert pipeline extended to Command Center (sound + flash + browser notification + auto-zoom + pulsing markers)
- Test reports: `/app/test_reports/iteration_110.json`

### Journey Replay (2026-03-08)
- **Backend API**: `GET /api/replay/sessions` (list sessions) + `GET /api/replay/{session_id}` (event stream)
- **Event Types**: session_start, movement, session_end, idle_start, route_deviation, guardian_alert, incident_created, incident_acknowledged, caregiver_assigned, incident_resolved
- **Session List** (`/replay`): 30 sessions with risk badges (HIGH/SAFE/LOW), timestamps, alert counts, distance
- **Replay Player** (`/replay/:sessionId`): Dark Leaflet map + event timeline + playback controls
- **Playback Controls**: Play/Pause, Prev/Next, Rewind, Speed (0.5x/1x/2x/4x), Progress scrubber
- **Journey Trail**: Cyan dashed polyline showing movement path
- **Event Markers**: Color-coded circle markers for significant events (alerts=red, resolved=green, etc.)
- **Timeline Panel**: Clickable events with auto-scroll, current event highlighted cyan
- **Map Auto-Pan**: Smooth flyTo/panTo on each event with intelligent zoom
- **Navigation**: Links from Operator Dashboard (Quick Actions) and OperatorConsole (sidebar)
- Test report: `/app/test_reports/iteration_111.json` — 24/24 backend, all frontend tests passed

### Risk Heatmap Layer (2026-03-08)
- **Live heatmap** on Command Center map: 624 grid cells from 8-signal AI risk engine (hotspot, trend, forecast, activity, patrol, environment, session density, mobility anomaly)
- **Toggle**: "RISK HEATMAP ON/OFF" button at top-right of map
- **Legend**: Shows Critical, High Risk, Moderate zone counts + total zones analyzed
- **Visual**: Double-circle zones (outer glow + core) with pulsing animations — critical zones pulse at 2.5s, high at 3.5s
- **Data source**: `GET /api/operator/city-heatmap/live` (624 cells, 18 zones: 12 high, 108 moderate)
- Test report: `/app/test_reports/iteration_112.json` — 10/10 backend, all frontend tests passed

### Heatmap Zone Drill-Down (2026-03-08)
- **Click any risk zone** on Command Center map → Zone Intelligence Panel slides in (320px)
- **Composite Risk Score**: Large color-coded score (0-10) with gradient progress bar
- **8 AI Signal Breakdown**: Forecast Risk, Hotspot Density, Trend Growth, Activity Spike, Patrol Priority, Environment, Session Density, Mobility Anomaly — each with colored progress bar (red >7, amber >4, green <4)
- **Dominant Signal**: Auto-computed from highest weighted score
- **Recommended Action**: Context-aware (critical→"Immediate patrol deployment", high→"Increase caregiver presence", moderate→"Monitor zone")
- **Selected zone highlight**: Dashed border, brighter fill when clicked
- **Controls animation**: Toggle/legend shift left when panel opens (`transition: right 0.3s`)
- Test report: `/app/test_reports/iteration_113.json` — 17/17 backend, all frontend tests passed


## 2026-03-08 — Admin Panel Phase 2 (User & Facility CRUD Management)

### Users Tab Enhancements
- **Create User**: Admin-initiated account creation with email, name, phone, password, role, facility assignment
- **Activate/Deactivate**: Toggle user status via PATCH endpoint + inline button
- **Pagination**: Page-based (15 per page) with prev/next, page X of Y display
- **User Detail Expansion**: Click row to expand with email, phone, Cognito status, created date, inline role/facility/status editors
- **Filters**: Search by name/email, filter by role, facility, active status
- **Color-coded Role Badges**: admin=red, operator=amber, caregiver=green, guardian=blue

### Facilities Tab Enhancements
- **Facility Type**: New field (home/hospital/elder_care/community/smart_city) with badge display
- **Inline Edit**: Modal for editing name, type, address, city, state, phone, email, max users
- **Active/Inactive Toggle**: Status toggle with visual indicator
- **Capacity Bar**: Visual progress bar showing user_count/max_users
- **User Drill-down**: Click user count to view facility users

### Backend Additions
- `POST /api/admin/users` — Create user with role + facility assignment
- `PATCH /api/admin/users/{id}/status` — Toggle user active/inactive
- `PATCH /api/admin/facilities/{id}/status` — Toggle facility active/inactive
- Updated `GET /api/admin/users` with page-based pagination (page, page_size, total_pages)
- Added `facility_type` to facility model and all responses
- Added `is_active` to user model and all responses
- Migration: q1a2b3c4df01

### Testing
- 24/24 backend tests passed (100%)
- All frontend components verified (100%)
- No action items

---


## 2026-03-08 — Nagarik Command Center (Phase 15)

### Full-screen Real-time Safety Operations Dashboard
- **Page route**: `/command-center` (protected for admin/operator roles)
- **Dark theme**: Slate-900 background with CartoDB dark map tiles
- **7 components built**:
  1. **CommandCenterHeader** — Live system status bar: Active SOS, AI Alerts, Guardians, Incidents, Uptime with pulse animations
  2. **LiveSafetyMap** — React-Leaflet dark map with red pulsing SOS markers, blue journey markers, risk zone circles
  3. **IncidentFeed** — Real-time scrollable feed of SOS alerts, fall detections with severity badges, timestamps, click-to-zoom
  4. **AISafetyAlerts** — Risk Spikes, Heatmap Alerts, Behavior Anomalies counters + predictive alert list
  5. **GuardianJourneys** — Active journey monitoring with risk levels, ETA, idle/deviation status
  6. **SystemMetrics** — API latency p50/p95, DB pool usage bar, Redis status, queue depth
  7. **CommandCenterPage** — Main layout: 3-row grid (header, map+feed, 3 bottom panels)
- **Real-time updates**: SSE connection for live SOS/alert events + 10s auto-refresh
- **Navigation**: "Command Center" button added to Admin Panel
- **Data sources**: `/api/operator/command-center`, `/api/admin/monitoring/metrics`, `/api/admin/monitoring/queue-health`, SSE `/api/stream`

### Testing
- 14/14 backend tests passed (100%)
- All frontend components verified (100%)
- Map rendering, incident feed, severity badges, timestamps, auto-refresh all confirmed

---


## 2026-03-08 — Terraform Staging + Monitoring & Alerting + Redis Queue Layer

### Terraform Staging Environment (P1)
- Created `/app/infra/staging/` mirroring dev with production-appropriate settings
- Separate VPC (10.20.0.0/16) to isolate from dev
- Aurora: higher capacity (min=1, max=4), deletion_protection=true, engine 15.3
- Cognito User Pool for staging (reuse module)
- App SG with security-group-only Aurora access pattern
- Separate S3 state key (env/staging/terraform.tfstate)
- CloudWatch monitoring module included

### Monitoring & Alerting (P1)
- **CloudWatch Terraform module** (`infra/modules/monitoring/`):
  - SNS topic for alarm notifications
  - Aurora CPU, connections, freeable memory alarms
  - Custom alarms: SOS trigger spike, API latency >2s, API 5xx error rate
  - CloudWatch log group for application logs
  - Added to both dev and staging environments
- **Backend monitoring service** (`monitoring_service.py`):
  - Thread-safe in-memory metrics with rolling windows
  - API latency tracking (p50/p95 per endpoint), error rates, request counts
  - Emergency counters: SOS, guardian alerts, escalations, fake calls/notifications
  - AI Safety Brain: risk spikes, heatmap alerts, behavior anomalies
  - DB pool stats (pool_size, checked_out, overflow, status)
  - Redis stats integration
- **Monitoring middleware** (`monitoring_middleware.py`): auto-tracks all /api/ requests
- **Monitoring API endpoints**:
  - `GET /api/admin/monitoring/metrics` — comprehensive platform metrics
  - `GET /api/admin/monitoring/alerts` — recent alert history
  - `GET /api/admin/monitoring/queue-health` — Redis queue depth and stats
- **Frontend**: New "Monitoring" tab in Admin Panel with live metrics dashboard (auto-refresh 15s)
- **Service hooks**: SOS, Fake Call, Fake Notification, Safety Brain wired to record metrics

### Redis Queue Layer (P1)
- **Redis Streams-based** persistent event queues with consumer groups
- Three queue streams:
  - `Nagarik:stream:incident` — SOS events, critical alerts (priority queue)
  - `Nagarik:stream:ai_signal` — Risk signals, heatmap events, behavior alerts (batch processing)
  - `Nagarik:stream:notification` — Guardian notifications, operator alerts, push messages
- Consumer groups for each stream with XREADGROUP/XACK pattern
- In-memory fallback queues when Redis unavailable (deque-based, maxlen capped)
- Queue worker framework with retry logic (`run_worker`, `consume_batch`, `acknowledge`)
- Processing stats tracking (enqueued, processed, failed per queue)
- Wired into: SOS service, Safety Brain, Notification service

### Testing
- 13/13 backend tests passed (100%)
- Frontend monitoring tab fully verified (all sections)
- Terraform files reviewed and verified (staging, monitoring module)

---

## 2026-03-08 — Infrastructure Hardening & DB Session Refactoring
### Aurora Security Group Hardening (P0)
- Replaced VPC CIDR-based ingress rule with security group-based access only
- Aurora module now accepts `allowed_security_group_ids` variable instead of `vpc_cidr`
- Created application security group (`Nagarik-dev-app-sg`) in dev environment for future ECS tasks
- Aurora DB only accessible from app security group — no public or VPC-wide access

### Aurora Engine Version Pinning (P0)
- Pinned PostgreSQL engine version to `15.3` (stable, LTS-level)
- Added `auto_minor_version_upgrade = false` to Aurora instance to prevent AWS auto-upgrades
- Updated default in Aurora module variables from 15.4 to 15.3

### Persistent DB Sessions (P0)
- Enhanced SQLAlchemy connection pool: `pool_size=20, max_overflow=10, pool_timeout=30, pool_recycle=1800, pool_pre_ping=True`
- Refactored `night_guardian_engine.py` from in-memory dict (`_sessions`) to DB-backed `GuardianSession`/`GuardianAlert` models
- Added 11 new columns to `guardian_sessions` table (migration p1a2b3c4de01): route_points, previous_location, previous_update_at, zone_id, route_deviation_m, idle_since, idle_duration_s, alert_count, last_alert_at, safety_check_pending, safety_check_sent_at
- All Night Guardian API endpoints now pass DB session to engine functions
- Fixed MultipleResultsFound bug by using `.order_by().limit(1)` and cleaning stale sessions on start
- Session state survives server restarts and works across multiple ECS containers

### Testing
- 19/19 backend tests passed (100%) — Night Guardian DB persistence fully verified
- Terraform files reviewed and verified (SG hardening, engine pinning, auto-upgrade disabled)
- System health check confirmed healthy

---


## 2026-03-08 — Phase 12: AWS Cognito Auth Integration
### Added
- **Dual-mode auth system** — Cognito when `COGNITO_USER_POOL_ID` env var is set, local JWT otherwise
- **Backend Cognito service** (`app/core/cognito.py`):
  - Full Cognito User Pool operations: sign_up, sign_in, refresh_tokens, verify JWT (JWKS), admin_create_user, admin_confirm_user, global_sign_out
  - SECRET_HASH support for App Clients with secret
  - JWKS caching with 1hr TTL
- **Updated auth routes** with new response shape: `{access_token, token_type, role, refresh_token, cognito_id_token, auth_provider}`
- **New endpoints:** `GET /api/auth/cognito-status`, `POST /api/auth/refresh`, `POST /api/auth/confirm`
- **Dual JWT verification** in `core/security.py` — tries local JWT first, Cognito JWKS second
- **Auto-provisioning** in `api/deps.py` — on Cognito token, creates/links local DB user automatically
- **Database:** Added `cognito_sub` column to users table (migration m1a2b3c4db01)
- **User service:** `get_user_by_cognito_sub()` and `auto_provision_cognito_user()` functions
- **Frontend AuthContext:** Stores `auth_provider` in localStorage, schedules Cognito token refresh 2min before expiry
- **Terraform module:** `infra/modules/cognito/main.tf` — Cognito User Pool + App Client (ready for `terraform apply`)

### Testing
- 16/18 backend tests passed (2 false positives: tested non-existent `/guardian-ai/status` path)
- Login, register, cognito-status, refresh, confirm endpoints verified
- All protected endpoints confirmed working with local JWT
- Frontend login flow verified via Playwright screenshot
- Backward compatibility: existing users work with no changes

### Activation Steps
1. Add `cognito-idp:*` IAM permissions to `Nagarik-ses-user` (or use Terraform module)
2. Provision User Pool (Terraform or boto3 script)
3. Add to backend `.env`: `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`
4. Restart backend — system auto-switches to Cognito mode

## 2026-03-08 — Phase 12b: Google OAuth Social Login
### Added
- **Google Sign-In** — One-click Google authentication on login and registration pages
- **Backend:** `POST /api/auth/google` (credential flow), `POST /api/auth/google/code` (authorization code flow), `GET /api/auth/google/status`
- **Google ID token verification** via Google's `oauth2.googleapis.com/tokeninfo` endpoint
- **Auto-provisioning:** On first Google sign-in, creates local DB user with `cognito_sub=google_{sub}`
- **Frontend:** `@react-oauth/google` GoogleOAuthProvider, "Sign in with Google" button on login + registration pages
- **Config:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (backend), `REACT_APP_GOOGLE_CLIENT_ID` (frontend)
- **Google Console:** Preview URL whitelisted — no origin errors

### Testing
- 19/19 backend tests passed
- Frontend: Google Sign-In iframe renders, button visible on both pages
- Domain whitelisting confirmed

### Cognito User Pool Provisioned
- **Pool ID:** `ap-south-1_kud9MGhBn`
- **App Client:** `om8f1550kktado1780j1j8qk3`
- **Users migrated:** Guardian + Operator (both CONFIRMED)
- **Token refresh:** Fixed SECRET_HASH — uses `cognito_username` (UUID) instead of email
- Full Cognito flow verified: Login → auth → local JWT + refresh_token + cognito_id_token + cognito_username


## 2026-03-08 — Phase 13: RBAC with Cognito Groups
### Added
- **5 Cognito groups:** admin, guardian, operator, caregiver, user
- **Users assigned:** Guardian user has [guardian, admin], Operator has [operator]
- **`require_role()` middleware** in `core/rbac.py`: checks JWT `cognito:groups` + DB role
- **Role hierarchy:** admin(5) > operator(4) > caregiver(3) > guardian(2) > user(1)
- **All API endpoints** protected with role-based access
- **JWT enhanced:** includes `cognito:groups` array in local JWT
- **Role sync:** On login, DB role synced to highest Cognito group
- **`GET /api/auth/me`:** Returns role, roles, facility_id, cognito_sub
- **`facility_id` column** added to users table (migration n1a2b3c4dc01)
- **Frontend:** `user.roles` from JWT; family tab routes to /family always

### Testing
- 19/19 backend + all frontend passed (100%)

---

## 2026-03-08 — Phase 11: Voice Escape Trigger
### Added
- **Voice Escape Trigger** — Hands-free activation of escape mechanisms using voice commands
- **Backend:** 6 API endpoints under `/api/voice-trigger/` prefix
  - Commands CRUD with auto-seeded defaults (help me→SOS, call me now→Fake Call, notify me now→Fake Notification)
  - Text-based recognition with fuzzy matching (substring + SequenceMatcher)
  - Audio-based recognition via OpenAI Whisper transcription + command matching
  - Recognition history with triggered/no_match status logging
- **Database:** `voice_command_configs` and `voice_trigger_logs` tables (Alembic migration l1a2b3c4da01)
- **Frontend VoiceTriggerPage:**
  - Live Voice Recognition: Mic button (MediaRecorder API) + text input fallback
  - Voice Commands: Color-coded cards by action type (SOS/red, Call/blue, Notification/violet)
  - Add Command form: phrase input, action select, confidence threshold slider
  - Delete button for custom (non-default) commands
  - Recognition result display: triggered status, confidence %, matched phrase, linked action
  - Expandable recognition history with timestamps and status
  - "How It Works" guide section
- **SSE:** `voice_trigger_activated` handler in FamilyDashboard auto-triggers escape overlays (FakeCallScreen, NotificationOverlay, SOS)
- **Navigation:** "Voice Trigger" link in sidebar with Mic icon

### Testing
- 27/27 backend tests passed (pytest)
- All frontend UI elements verified via Playwright
- Text-based recognition confirmed for all 3 default commands
- Add/delete custom commands verified
- SSE handler confirmed working

---

## 2026-03-08 — Phase 10: Guardian AI Predictive Intelligence
### Added
- **Guardian AI Prediction Engine** — Fuses 3-Layer Safety Brain data (50/25/25 weighting)
  - Risk classification: LOW (<35%), MODERATE (35-60%), HIGH (60-85%), CRITICAL (85%+)
  - Action thresholds: ≥60% Notification, ≥75% Call, ≥85% SOS Pre-arm
  - Sensitivity multiplier: Low (0.8x), Medium (1.0x), High (1.2x)
  - Non-linear escalation for 2+ high-severity factors
- **Backend:** 6 API endpoints under `/api/guardian-ai/`
  - Config auto-creates with defaults (medium sensitivity, thresholds 0.6/0.75/0.85, 30min cooldown)
  - Predict-risk pulls real-time status, location risk, behavioral analysis, generates narrative
  - Accept/Dismiss updates prediction status with responded_at timestamp
  - History sorted by created_at DESC
- **Database:** `guardian_ai_configs` and `guardian_ai_predictions` tables
- **Frontend GuardianAIPage:**
  - Risk score circular gauge with level badge and confidence
  - Recommended action card with icon, urgency badge, Accept/Dismiss buttons
  - Layer breakdown: Real-time (50%), Location (25%), Behavioral (25%) progress bars
  - Risk factors with severity badges
  - AI narrative section
  - Sensitivity & Thresholds config: dropdown, 3 sliders, toggles, cooldown input
  - Expandable prediction history with status badges
- **SSE:** `guardian_ai_alert` handler with toast notifications (error for critical/high, warning for moderate)

### Testing
- 27/27 backend tests passed (pytest)
- All frontend UI elements verified via Playwright
- Escape Layer (Call/Notification/SOS) backward compatibility confirmed

---

## 2026-03-08 — Phase 9: SOS Silent Mode (ESCAPE LAYER COMPLETE)
### Added
- **SOS Silent Mode** — Covert emergency trigger system completing the 3-tool Escape Layer
- **Backend:** 5 API endpoints under `/api/sos/` prefix
  - Config GET/PUT with auto-created defaults (enabled, chain notification/call, voice keywords, silent mode, auto-share location)
  - Trigger creates active SOS, returns chain info, broadcasts SSE to user + operators
  - Cancel resolves SOS with resolved_by/at, broadcasts sos_resolved SSE
  - History returns sorted SOS logs with chain flags and location
- **Database:** `sos_configs` and `sos_logs` tables
- **Frontend SOSPage:**
  - Big red trigger widget (w-32 h-32 circular button)
  - Chain Escape Sequence config: Step 1 Auto Fake Notification (10s default), Step 2 Auto Fake Call (40s default, "Boss")
  - Voice Keywords & Settings: enabled/silent/auto-location toggles, removable keyword badges
  - Active SOS banner (red pulsing, cancel button, chain countdown)
  - Expandable SOS History with chain flags, status badges, timestamps
- **SSE Events:** `sos_triggered` (auto-chains FakeNotification → FakeCall via setTimeout), `sos_resolved`
- **Navigation:** "SOS Silent Mode" in sidebar with RED highlight (bg-red-600)

### Escape Layer Summary
1. **Escape Call** (Phase 7) — Simulated incoming call | 7 endpoints | 19 tests
2. **Escape Notification** (Phase 8) — Simulated push notification | 7 endpoints | 25 tests
3. **SOS Silent Mode** (Phase 9) — Covert emergency + chain | 5 endpoints | 26 tests

### Testing
- 26/26 backend tests passed (pytest)
- All frontend UI elements verified via Playwright
- Escape Call + Escape Notification backward compatibility confirmed
- Chain sequence (SOS → Notification → Call) logic verified in SSE handler

---

## 2026-03-08 — Phase 8: Fake Notification Escape Mechanism
### Added
- **Escape Notification System** — Simulated push notifications for covert escape
- **Backend:** 7 API endpoints under `/api/fake-notification/` prefix
  - Presets CRUD with auto-seeded defaults (Team Meeting/Work, Package/Delivery, Security Alert/Security, Mom Message/Message)
  - Trigger with delay scheduling (0-300 seconds)
  - Complete with viewed/dismissed/send_alert flags
  - History sorted by triggered_at DESC
- **Database:** `fake_notification_presets` and `fake_notification_logs` tables
- **Frontend FakeNotificationPage:** Preset grid (2-col) with category-colored cards, delay selector, create form, expandable history
- **Frontend NotificationOverlay:** 2-phase component:
  - Banner: Slides from top, category icon/label, title/message, View/Dismiss action bar, auto-dismiss 12s
  - Action overlay: Centered modal with "Alert Trusted Contacts" / "I'm Safe — Dismiss"
- **SSE Events:** `fake_notification_incoming` triggers banner, `escape_alert` post-action alert
- **Navigation:** "Escape Notification" link in sidebar between Escape Call and Route Monitor

### Testing
- 25/25 backend tests passed (pytest)
- All frontend UI elements verified via Playwright
- Escape Call (Phase 7) backward compatibility confirmed
- SSE handlers confirmed working

---

## 2026-03-08 — Phase 7: Fake Call Escape Mechanism
### Added
- **Fake Call System** — Full escape call feature for exiting dangerous situations
- **Backend:** 7 API endpoints under `/api/fake-call/` prefix
  - Presets CRUD (GET/POST/PUT/DELETE) with auto-seeded defaults (Mom, Boss, Best Friend)
  - Trigger endpoint with delay scheduling (0-300 seconds)
  - Complete endpoint with optional trusted contact alert
  - History endpoint with sorted call logs
- **Database:** `fake_call_presets` and `fake_call_logs` tables (SQLAlchemy models)
- **Frontend FakeCallPage:** Preset grid with color-coded cards (Family/Work/Friend/Medical/Custom), delay selector, create preset form, expandable call history
- **Frontend FakeCallScreen:** Full-screen overlay component with 3 phases:
  - Ringing: Caller avatar, Accept/Decline buttons, animated phone icon
  - Active: Call timer, mute/speaker controls, end call button
  - Post-call: "Alert Trusted Contacts + Share Location" / "I'm Safe — Dismiss" flow
- **SSE Events:** `fake_call_incoming` triggers call overlay, `escape_alert` sends post-call alert
- **Navigation:** "Escape Call" link in sidebar between Safety Brain and Route Monitor

### Testing
- 19/19 backend tests passed (pytest)
- All frontend UI elements verified via Playwright (preset cards, call phases, form, history)
- SSE handlers confirmed working

---

## 2026-03-07 — Phase 6: 3-Layer AI Safety Brain
### Added
- **Location Intelligence Engine** (`location_intelligence.py`) — Grid-based spatial danger scoring with 100m cells, incident density (50%), time-of-day risk (30%), recency boost (20%)
- **Behavioral Pattern Analyzer** (`behavior_analyzer.py`) — Multi-window (7/14/30 day) anomaly detection across wandering, falls, voice distress, safety events with temporal clustering
- **Risk Fusion Engine** (`risk_fusion.py`) — 3-layer weighted fusion: Real-time (50%) + Location (25%) + Behavior (25%), voice distress floor override at 80%
- **Predictive Alert Engine** (`predictive_alerts.py`) — Confidence-tiered alerts (Low/Medium/High) with SSE broadcast
- **AI Safety Narrative** — GPT-5.2 generates human-readable safety summaries (explains, never calculates)
- **Danger Heatmap** — Grid-based hotspot data for map overlays
- **API Endpoints (safety-brain/v2):**
  - `GET /api/safety-brain/v2/fused-risk/{user_id}` — Full 3-layer fused risk
  - `GET /api/safety-brain/v2/location-risk/{user_id}` — Location danger score  
  - `GET /api/safety-brain/v2/behavior/{user_id}` — Behavioral analysis (7/14/30 day)
  - `GET /api/safety-brain/v2/predictive/{user_id}` — Predictive alert + AI narrative
  - `GET /api/safety-brain/v2/heatmap` — Danger heatmap data points
- **Frontend Safety Radar UI:**
  - 3-layer risk breakdown cards (Real-time/Location/Behavioral)
  - Risk gauge with level badge
  - Signal breakdown bars with decay visualization
  - Behavioral event timeline (7d/14d/30d stacked bars)
  - AI narrative section with GPT-5.2 toggle
  - Detected patterns with severity badges
  - Danger hotspot grid with intensity indicators
  - Recommendation cards
- **SSE:** `predictive_safety_alert` handler in FamilyDashboard, passed to SafetyBrainDashboard as prop
- **Bug Fix:** Fixed `get_user_risk_status` call in `safety_brain_v2.py` (missing `await` and `session` arg)

### Testing
- 26/26 backend tests passed (pytest)
- All frontend UI elements verified via Playwright
- V1 backwards compatibility confirmed (status, events, evaluate)
- GPT-5.2 AI narrative generation confirmed working
- SSE predictive_safety_alert handler confirmed

---

## 2026-03-07 — Phase 5: Whisper Voice Verification
### Added
- **Whisper Verification Service** (`whisper_verification_service.py`) — Cloud-level distress detection using OpenAI Whisper
- **Async worker architecture** — Non-blocking: audio queued → background Whisper transcription → analysis
- **Semantic distress analysis** — Weighted multi-category scoring: help phrases (+3), fear language (+2), aggressive words (+2), shouting markers (+2), repetition (+1), exact phrase matching (bonus)
- **Multi-language support** — English, Hindi, Hinglish distress phrases (40+ patterns)
- **Confidence formula:** keyword×0.35 + scream×0.20 + transcript_distress×0.35 + repetition×0.10
- **API Endpoints:**
  - `POST /api/sensors/voice-distress/verify` — Upload audio (returns queued, non-blocking)
  - `GET /api/sensors/voice-distress/{id}` — Get verification result
  - `POST /api/sensors/voice-distress/{id}/re-verify` — Guardian re-verification
- **Safety Brain integration** — Whisper-verified signals get 20% confidence boost
- **SSE Event:** `voice_verification_complete` broadcast with transcript + confidence
- **Privacy safeguards** — Audio deleted after processing, transcript-only storage, 5MB max
- **DB Migration:** Added whisper_confidence, verification_status, distress_phrases_found, trigger_type to voice_distress_events
- **Frontend:** Voice Distress card shows WHISPER VERIFIED badge, transcript display, confidence bar, detected phrases as tags, distress level badge (emergency/high_alert/caution)

### Testing
- Audio upload + queued status confirmed
- Whisper transcription (async background) verified
- Confidence scoring validated for English, Hindi, Hinglish distress phrases
- Normal conversation correctly scores 0 (no false positives)
- Re-verification endpoint confirmed working
- Rapid uploads (no cooldown blocking) confirmed
- Safety Brain integration confirmed (voice signal updated)
- Events list includes all new Whisper fields

---

## 2026-03-07 — Phase 4: Predictive Safety Rerouting
### Added
- **Predictive Reroute Service** (`predictive_reroute_service.py`) — Proactive route intelligence
- **4-Factor Route Safety Score:** 0.35×IncidentProximity + 0.25×SafeZoneDistance + 0.20×TimeOfDay + 0.20×PathEfficiency
- **Auto-trigger:** Safety Brain fires reroute at Dangerous (≥0.6) via `on_risk_level_change` hook
- **Manual trigger:** Guardian can request reroute anytime via API
- **OSRM integration:** Fetches alternative routes, scores each, picks safest
- **Cooldown:** 120s between suggestions per user
- **API Endpoints:**
  - `POST /api/reroute/suggest` — Compute safer route
  - `POST /api/reroute/{id}/approve` — Guardian approves reroute
  - `POST /api/reroute/{id}/dismiss` — Guardian dismisses suggestion
  - `GET /api/reroute/history` — Past reroute suggestions
- **SSE Events:** `safety_reroute_suggestion`, `safety_reroute_approved`
- **DB Migration:** `reroute_suggestions` table (j1a2b3c4d801)
- **Frontend:**
  - EmergencyMap: dashed green line for suggested route, suggestion card with approve/dismiss
  - FamilyDashboard: SSE handlers for reroute events, toast notifications

### Testing
- 18/18 backend tests passed (pytest)
- Frontend UI elements verified via Playwright
- Approve/dismiss flow confirmed working
- Safety Brain auto-trigger hook confirmed

---

## 2026-03-07 — Phase 3: Nagarik Brain
### Added
- **Safety Brain Service** (`safety_brain_service.py`) — Central intelligence layer fusing 5 detector signals into unified risk score
- **Risk Formula:** fall×0.35 + voice×0.30 + route×0.15 + wander×0.10 + pickup×0.10
- **Risk Levels:** Normal (<30%), Suspicious (30-60%), Dangerous (60-85%), Critical (≥85%)
- **Signal Decay:** Exponential decay per signal type (Fall: 60s, Voice: 45s, Route: 120s, Wander: 180s, Pickup: 90s)
- **Active Risk State Cache:** In-memory dict with Redis-ready architecture
- **Auto-SOS:** Triggered only at Critical level (≥85%)
- **API Endpoints:**
  - `POST /api/safety-brain/evaluate` — Compute unified risk
  - `GET /api/safety-brain/status/{user_id}` — Current decayed risk state
  - `GET /api/safety-brain/events` — List recent safety events
  - `POST /api/safety-brain/{event_id}/resolve` — Resolve event
- **Detector Integration:** All 5 detectors now feed signals to Safety Brain via hooks:
  - `on_fall_detected()` in fall_detection_service.py
  - `on_voice_distress()` in voice_distress_service.py
  - `on_wandering_detected()` in wandering_detection_service.py
  - `on_route_deviation()` in route_monitor_service.py
  - `on_pickup_anomaly()` in pickup_verification_service.py
- **SSE Event:** `safety_risk_alert` broadcast for all non-normal events
- **Existing detector SSE events preserved** (augmented, not replaced)
- **DB Migration:** `safety_events` table (i1a2b3c4d701)
- **Frontend:**
  - Safety Brain Dashboard page (`/family/safety-brain`) with risk gauge, signal breakdown bars (with decay visualization), risk classification legend, recent events list
  - EmergencyMap integration: Safety Brain card in side panel + circular map marker (pulsing for critical)
  - FamilyDashboard: SSE handler for `safety_risk_alert`, colored banner for active events, nav link with Brain icon

### Testing
- 23/23 backend tests passed (pytest)
- All frontend UI elements verified
- Detector-to-Brain integration confirmed for fall and voice
- Risk thresholds verified at all 4 boundaries
- Auto-SOS confirmed only at critical level

---

## Previous Phases (Summary)
- **Phase 2:** Live Route Monitoring, Fall Detection (5-stage), Wandering Detection, Pickup Verification (QR/PIN), Voice Distress Detection
- **Phase 1:** Core platform (auth, dashboards, devices, telemetry, incidents, notifications, SSE)
