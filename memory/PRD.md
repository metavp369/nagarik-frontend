# Nagarik - Digital Care Monitoring Platform

## Original Problem Statement
Build "Nagarik," a production-grade, AWS-native full-stack digital care monitoring and escalation platform for elderly individuals. The initial phase focuses on a public-facing marketing website and investor-ready demo experience for the domain `Nagarik.care`.

## Tech Stack
- **Frontend:** React (CRA), Tailwind CSS, Shadcn/UI, Leaflet Maps
- **Backend:** FastAPI, SQLAlchemy (async), PostgreSQL, Redis
- **Integrations:** AWS Cognito, Firebase (FCM), Twilio, SendGrid, OpenAI GPT-5.2 (via Emergent LLM Key), Mapbox, slowapi

## Core Features - COMPLETED

### Marketing Website (Dark Enterprise Theme)
- Homepage (`/`) with live intelligence ticker, City Safety Simulation
- Investor Page (`/investors`) with 7 sections
- Pilot Signup Page (`/pilot`) with lead capture + email notification
- WhatsApp support button on all marketing pages
- AI Chatbot ("Ask Nagarik AI") with GPT-5.2 integration

### Platform Features
- Live Telemetry Dashboard (`/telemetry`) with real anonymized data
- Public Safety Dashboard (`/safety-dashboard`) with incident feeds
- System Status Page (`/system-status`) with 8 modules, 90-day uptime, incidents log
- Command Center with Demo Mode toggle
- Mobile PWA with Shake-to-SOS, Live Guardian Map, Incident Replay
- Notification Preferences (`/m/notification-settings`) with toggleable categories
- API Rate Limiting + Security Headers

### Backend APIs
- `POST /api/auth/login` - JWT authentication
- `POST /api/pilot/signup` - Pilot lead capture
- `POST /api/chatbot` - AI chatbot messages
- `GET /api/status/platform` - Platform telemetry + system modules
- `GET /api/status/events` - Live anonymized events
- `GET /api/status/metrics` - Network growth metrics
- `GET /api/status/incidents` - Active incidents
- `GET /api/status/risk-intelligence` - AI risk analysis
- `GET/PUT /api/settings/notifications` - User notification preferences

## Testing Status (March 10, 2026)
- Backend: 100% (17/17 tests passed)
- Frontend: 100% (all features working)
- Test report: `/app/test_reports/iteration_135.json`

## Known Mocked Data
- System module uptimes on Status Page are hardcoded (not from real CloudWatch/Prometheus)
- 90-day uptime history is randomly generated per session
- Recent incidents on Status Page are static demo data

## Credentials
- Admin: Nagarik4parents@gmail.com / secret123

## Backlog (Prioritized)

### P1 - Near Term
- Command Center performance optimization (currently 5+ sec load)
- Connect System Status Page to real monitoring (CloudWatch/Prometheus)

### P2 - Medium Term
- Native Mobile App Build (React Native) - deferred until after pilot deployments
- Learning Loop (AI training module)
- Unified MessagingService for push + email

### P3 - Future
- Multi-tenancy dashboards for institutional clients
- Subdomain architecture (app.Nagarik.care, status.Nagarik.app)
