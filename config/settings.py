"""Настройки приложения"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OllamaSettings:
    """Настройки Ollama"""
    base_url: str = "http://localhost:11434"
    model: str = "phi:2.7b"  # Используем доступную модель вместо llama3
    timeout: int = 60
    temperature: float = 0.1
    max_retries: int = 3
    retry_delay: int = 2


@dataclass
class RatingSettings:
    """Настройки оценки"""
    target_aht_minutes: int = 12
    target_aht_seconds: int = 720  # 12 минут в секундах
    slow_response_threshold: int = 60  # секунд
    max_messages_penalty: int = 10
    max_messages_per_minute: int = 4


@dataclass
class AppSettings:
    """Общие настройки приложения"""
    ollama: OllamaSettings = field(default_factory=OllamaSettings)
    rating: RatingSettings = field(default_factory=RatingSettings)
    default_limit: Optional[int] = None
    output_json: str = "results.json"
    output_csv: str = "results.csv"


# Глобальный экземпляр настроек
settings = AppSettings()