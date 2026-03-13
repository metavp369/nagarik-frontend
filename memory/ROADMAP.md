# Nagarik - Roadmap

## P0 — Completed
- [x] Operator Dashboard (Incident Dispatch) — March 8, 2026
- [x] Caregiver Dashboard (Field Response) — March 8, 2026
- [x] Real-Time Alert System (Sound + Flash + Browser Notification + Pulsing Markers) — March 8, 2026
- [x] Command Center Alert Integration — March 8, 2026
- [x] Journey Replay (Session List + Map Playback + Timeline) — March 8, 2026
- [x] Risk Heatmap Layer on Command Center (624 cells, toggle, legend, pulsing zones) — March 8, 2026
- [x] Heatmap Zone Drill-Down (Zone Intelligence Panel with 8 AI signals) — March 8, 2026
- [x] Simulation History (Immutable Research Log) — March 4, 2026
- [x] Multi-Metric Instability Escalation (Step 1) — March 4, 2026
- [x] Multi-Metric Instability Auto-Recovery (Step 2) — March 4, 2026
- [x] Escalation Analytics Dashboard (Step 1 — Backend KPIs) — March 4, 2026
- [x] Escalation Analytics Dashboard (Step 2 — Frontend UI) — March 4, 2026
- [x] Multi-Metric Simulation Comparison Engine (Step 1 — Backend + Step 2 — Frontend UI) — March 4, 2026

## P1 — High Priority (Next)
- [ ] Guardian AI Refinement: Use historical data to retrain and improve predictive AI
- [ ] AI Replay Analysis: AI-generated insights per journey (response time, risk probability, delay analysis)

## P2 — Medium Priority
- [ ] Mobile App: Native mobile application for guardians
- [ ] Priority Alert Types: Different sounds for critical/high/medium severity
- [ ] Anomaly Visualization: Sparkline charts for metric trends over time
- [ ] Aurora Security Group: Narrow ingress in `/app/infra/modules/aurora/main.tf` from VPC CIDR to specific source
- [ ] Aurora Engine Version: Re-evaluate pinned version `14` in `/app/infra/dev/main.tf`

## P3 — Future
- [ ] React Native mobile app (parent-facing)
- [ ] Deploy staging/production on AWS using existing Terraform
- [ ] AWS Cognito integration for user management
- [ ] AI-powered fall detection from sensor data

## Refactoring
- [ ] Extract inline page components from OperatorConsole.jsx (DashboardPage, IncidentsPage, DeviceHealthPage) into separate files
