# Main API Router
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.seniors import router as seniors_router
from app.api.devices import router as devices_router
from app.api.telemetry import router as telemetry_router
from app.api.incidents import router as incidents_router
from app.api.dashboard import router as dashboard_router
from app.api.device_telemetry import router as device_telemetry_router
from app.api.stream import router as stream_router
from app.api.push import router as push_router
from app.api.operator import router as operator_router
from app.api.my import router as my_router
from app.api.safety import router as safety_router
from app.api.night_guardian import router as night_guardian_router
from app.api.safe_route import router as safe_route_router
from app.api.guardian import router as guardian_router
from app.api.predictive_alert import router as predictive_alert_router
from app.api.guardian_dashboard import router as guardian_dashboard_router
from app.api.safety_score import router as safety_score_router
from app.api.emergency import router as emergency_router
from app.api.route_monitor import router as route_monitor_router
from app.api.sensors import router as sensors_router
from app.api.zones import router as zones_router
from app.api.pickup import router as pickup_router
from app.api.safety_brain import router as safety_brain_router
from app.api.reroute import router as reroute_router
from app.api.safety_brain_v2 import router as safety_brain_v2_router
from app.api.fake_call import router as fake_call_router
from app.api.fake_notification import router as fake_notification_router
from app.api.sos import router as sos_router
from app.api.guardian_ai import router as guardian_ai_router
from app.api.voice_trigger import router as voice_trigger_router
from app.api.google_auth import router as google_auth_router
from app.api.admin import router as admin_router
from app.api.monitoring import router as monitoring_router
from app.api.caregiver import router as caregiver_router
from app.api.replay import router as replay_router
from app.api.guardian_ai_v2 import router as guardian_ai_v2_router
from app.api.guardian_network import router as guardian_network_router
from app.api.safety_events import router as safety_events_router
from app.api.realtime_events import router as realtime_events_router
from app.api.device import router as device_router
from app.api.guardian_live import router as guardian_live_router
from app.api.guardian_incidents import router as guardian_incidents_router
from app.api.demo import router as demo_router
from app.api.pilot import router as pilot_router
from app.api.status import router as status_router
from app.api.chatbot import router as chatbot_router
from app.api.notification_settings import router as notif_settings_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(seniors_router)
api_router.include_router(devices_router)
api_router.include_router(telemetry_router)
api_router.include_router(incidents_router)
api_router.include_router(dashboard_router)
api_router.include_router(device_telemetry_router)
api_router.include_router(stream_router)
api_router.include_router(push_router)
api_router.include_router(operator_router)
api_router.include_router(my_router)
api_router.include_router(safety_router)
api_router.include_router(night_guardian_router)
api_router.include_router(safe_route_router)
api_router.include_router(guardian_router)
api_router.include_router(predictive_alert_router)
api_router.include_router(guardian_dashboard_router)
api_router.include_router(safety_score_router)
api_router.include_router(emergency_router)
api_router.include_router(route_monitor_router)
api_router.include_router(sensors_router)
api_router.include_router(zones_router)
api_router.include_router(pickup_router)
api_router.include_router(safety_brain_router)
api_router.include_router(reroute_router)
api_router.include_router(safety_brain_v2_router)
api_router.include_router(fake_call_router)
api_router.include_router(fake_notification_router)
api_router.include_router(sos_router)
api_router.include_router(guardian_ai_router)
api_router.include_router(voice_trigger_router)
api_router.include_router(google_auth_router)
api_router.include_router(admin_router)
api_router.include_router(monitoring_router)
api_router.include_router(caregiver_router)
api_router.include_router(replay_router)
api_router.include_router(guardian_ai_v2_router)
api_router.include_router(guardian_network_router)
api_router.include_router(safety_events_router)
api_router.include_router(realtime_events_router)
api_router.include_router(device_router)
api_router.include_router(guardian_live_router)
api_router.include_router(guardian_incidents_router)
api_router.include_router(demo_router)
api_router.include_router(pilot_router)
api_router.include_router(status_router)
api_router.include_router(chatbot_router)
api_router.include_router(notif_settings_router)
