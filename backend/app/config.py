from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # SQLite by default so the app runs with zero setup; docker-compose sets Postgres.
    database_url: str = "sqlite:///./doriishonch.db"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    cors_origins: str = "http://localhost:3000"
    seed_on_startup: bool = True
    pharmacy_region: Literal["", "Namangan"] = "Namangan"
    # Xodimlar login. Xaridorlar uchun login yoʻq.
    auth_enabled: bool = True
    secret_key: str = ""  # boʻsh boʻlsa backend/.secret fayli avtomatik yaratiladi
    show_demo_accounts: bool = True
    # Production: ENVIRONMENT=production — SECRET_KEY majburiy, demo hisoblar yashiriladi, API hujjatlari yopiladi
    environment: str = "development"
    rate_limit_enabled: bool = True
    rate_limit_write_per_min: int = 60  # tekshirish, xabar, ball, AI — bitta IP dan daqiqasiga
    rate_limit_login_per_min: int = 10
    rate_limit_read_per_min: int = 600
    trust_proxy: bool = True  # backend faqat ichki tarmoqda: IP ni proksi sarlavhalaridan olamiz
    max_upload_mb: int = 8
    # Oʻz ML modellarimiz (skan xavf modeli) saqlanadigan papka
    ml_dir: str = "ml_data"
    # True: bazadagi dori reestri toʻliq (haqiqiy). False: nomaʼlum GTIN "roʻyxatdan oʻtmagan" deb
    # belgilanmaydi, faqat kod tuzilishi va DoriIshonch zanjiri tekshiriladi.
    registry_complete: bool = False
    # Foydalanuvchiga koʻrsatiladigan vaqt (bazada UTC saqlanadi). Toshkent: UTC+5
    display_utc_offset_hours: int = 5
    # Asl Belgisi xTrace Open API. Kalit boʻlmasa, demo baza ishlatiladi.
    # Test muhiti: https://xtrace.stage.aslbelgisi.uz, production: https://xtrace.aslbelgisi.uz
    asl_belgisi_base_url: str = "https://xtrace.stage.aslbelgisi.uz"
    asl_belgisi_api_key: str = ""
    # OpenStreetMap Overpass (haqiqiy dorixonalar roʻyxati, kalit kerak emas)
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    # Bojxona tizimi API (rasmiy kelishuvdan keyin). Boʻsh boʻlsa demo manba ishlatiladi.
    customs_api_url: str = ""
    customs_api_token: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("prod", "production")

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
