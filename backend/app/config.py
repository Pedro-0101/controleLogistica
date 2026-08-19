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
    static_dir: Path = BASE_DIR / "static"


settings = Settings()
