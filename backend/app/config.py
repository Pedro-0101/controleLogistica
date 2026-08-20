"""Configurações da aplicação carregadas de variáveis de ambiente / arquivo .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
PROJECT_DIR = BASE_DIR.parent  # controleLogistica/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg2://logistica:logistica@localhost:5432/controle_logistica"
    )
    anpr_lang: str = "en"
    imagens_dir: Path = PROJECT_DIR / "data" / "imagens"

    secret_key: str = "dev-secret-change-me-0123456789abcdef"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 10080
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"
    admin_nome: str = "Administrador"


settings = Settings()
