"""Вспомогательные функции"""

import subprocess
import sys
import requests
from typing import Optional


def check_ollama_process() -> bool:
    """Проверка запущен ли процесс Ollama"""
    # Проверяем через API
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass

    # Пробуем найти процесс в системе
    try:
        if sys.platform == "win32":
            result = subprocess.run(['tasklist', '/fi', 'imagename eq ollama.exe'],
                                  capture_output=True, text=True)
            if 'ollama.exe' in result.stdout:
                return True
        else:  # Linux/Mac
            result = subprocess.run(['pgrep', 'ollama'], capture_output=True)
            if result.returncode == 0:
                return True
    except:
        pass

    return False


def get_available_models() -> list:
    """Получить список доступных моделей Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [m.get('name') for m in models]
    except:
        pass
    return []


def format_time(seconds: int) -> str:
    """Форматирование времени в минуты и секунды"""
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes} мин {secs} сек"
    return f"{secs} сек"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."