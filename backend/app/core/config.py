# Centralized Configuration via Pydantic Settings
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ──
    app_name: str = "nischint"
    app_env: str = "dev"

    # ── JWT ──
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    # ── Database (Neon PostgreSQL) ──
    database_url: str

    # ── MongoDB (legacy status checks) ──
    mongo_url: str
    db_name: str

    # ── CORS ──
    cors_origins: str = "*"

    # ── SSE ──
    sse_ping_interval: int = 25

    # ── AWS SES ──
    aws_region: str = "ap-south-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    ses_from_email: str = ""
    email_provider: str = "stub"

    # ── Twilio SMS ──
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    sms_provider: str = "stub"

    # ── Firebase (FCM Push) ──
    firebase_sa_key_path: str = ""
    firebase_sa_key_json: str = ""
    firebase_project_id: str = "nischint-5f248"
    push_provider: str = "stub"

    # ── Escalation Thresholds (minutes) ──
    escalation_l1_minutes: int = 5
    escalation_l2_minutes: int = 10
    escalation_l3_minutes: int = 15
    escalation_check_interval: int = 60

    # ── Device Offline Detection ──
    device_offline_threshold_minutes: int = 10
    device_offline_cooldown_minutes: int = 15

    # ── Health Rule: Low Battery ──
    rule_low_battery_enabled: bool = True
    low_battery_threshold_percent: int = 20
    low_battery_sustain_minutes: int = 10
    low_battery_cooldown_minutes: int = 60
    low_battery_recovery_buffer_percent: int = 5

    # ── Health Rule: Signal Degradation ──
    rule_signal_degradation_enabled: bool = True
    signal_degradation_threshold_dbm: int = -80
    signal_degradation_sustain_minutes: int = 10
    signal_degradation_cooldown_minutes: int = 60
    signal_degradation_recovery_buffer_dbm: int = 5

    # ── Health Rule: Reboot Anomaly ──
    rule_reboot_anomaly_enabled: bool = True
    reboot_anomaly_max_reboots: int = 3
    reboot_anomaly_window_minutes: int = 60
    reboot_anomaly_cooldown_minutes: int = 120

    # ── Notification Worker ──
    worker_max_attempts: int = 5
    worker_batch_size: int = 20
    worker_poll_interval: int = 15
    worker_backoff_base: int = 30

    # ── AI Narrative Engine ──
    emergent_llm_key: str = ""

    # ── AWS Cognito ──
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_client_secret: str = ""

    # ── Google OAuth ──
    google_client_id: str = ""
    google_client_secret: str = ""

    # ── Redis Cache ──
    redis_url: str = ""

    # ── OSRM Routing ──
    osrm_url: str = ""

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
