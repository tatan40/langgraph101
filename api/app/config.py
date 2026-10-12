"""Configuration : lue depuis l'environnement (et le .env à la racine du repo)."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    # Jev — consignes en anglais, texte en français (retenu après l'étape 0)
    typesafe_api_key: SecretStr | None = None
    jev_lang: Literal["fr", "en"] = "en"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2:7b"
    ollama_temperature: float = 0.3

    # Politique de routage (seuils de départ, à calibrer sur de vraies données)
    min_confidence: float = 0.5        # en dessous : revue humaine
    escalade_threshold: float = 0.5    # au-dessus : revue humaine obligatoire
    reply_expected_min: float = 0.3    # en dessous : pas de réponse
    human_request_threshold: float = 0.5  # au-dessus : l'auteur veut un humain → revue humaine
    tons_display_threshold: float = 0.7
    verify_threshold: float = 0.5      # chaque contrôle qualité doit dépasser ce seuil
    # Contrôles où un « peut-être » ne suffit pas : seuil plus exigeant.
    strict_checks: tuple[str, ...] = ("traite_la_demande", "sans_fait_invente")
    verify_threshold_strict: float = 0.7
    max_attempts: int = 2              # nombre maximal de brouillons avant revue humaine

    # Langfuse (optionnel) : sans clés, le traçage est désactivé
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "http://localhost:3000"
    langfuse_project_id: str = "temperament-agent"   # = LANGFUSE_INIT_PROJECT_ID (infra/langfuse/.env)


settings = Settings()
