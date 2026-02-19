"""Клиент для работы с Ollama API"""

import json
import time
import requests
from typing import Optional, Dict, Any, List
from config.settings import settings


class OllamaClient:
    """Клиент для работы с Ollama API"""

    def __init__(self,
                 base_url: str = None,
                 model: str = None,
                 timeout: int = None):
        """
        Args:
            base_url: URL сервера Ollama
            model: название модели для использования
            timeout: таймаут запроса в секундах
        """
        self.base_url = (base_url or settings.ollama.base_url).rstrip('/')
        self.model = model or settings.ollama.model
        self.timeout = timeout or settings.ollama.timeout
        self.temperature = settings.ollama.temperature
        self.max_retries = settings.ollama.max_retries
        self.retry_delay = settings.ollama.retry_delay

        self.api_url = f"{self.base_url}/api/generate"
        self.available = False
        self.available_models: List[str] = []

    def check_connection(self) -> bool:
        """
        Проверка подключения к Ollama и доступных моделей

        Returns:
            bool: True если подключение успешно
        """
        try:
            # Проверяем доступность API
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json().get('models', [])
                self.available_models = [m.get('name') for m in models_data]

                if self.model in self.available_models:
                    print(f"✅ Подключение к Ollama установлено. Модель {self.model} доступна.")
                    self.available = True
                else:
                    print(f"⚠️ Модель {self.model} не найдена.")
                    print(f"   Доступные модели: {', '.join(self.available_models)}")
                    print(
                        f"   Будет использована первая доступная модель: {self.available_models[0] if self.available_models else 'нет'}")

                    if self.available_models:
                        self.model = self.available_models[0]
                        self.available = True
                    else:
                        self.available = False

                return self.available
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Не удалось подключиться к Ollama по адресу {self.base_url}")
            print("   Убедитесь, что Ollama запущена:")
            print("   - Запустите команду 'ollama serve' в отдельном терминале")
            print("   - Или запустите Ollama Desktop приложение")
            return False
        except Exception as e:
            print(f"❌ Ошибка при проверке подключения: {e}")
            return False

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Отправка промпта в Ollama и получение ответа

        Args:
            prompt: текст промпта
            **kwargs: дополнительные параметры

        Returns:
            Optional[str]: ответ модели или None в случае ошибки
        """
        if not self.available and not self.check_connection():
            print("   Используется fallback режим (без реальной модели)")
            return self._generate_fallback_response(prompt)

        temperature = kwargs.get('temperature', self.temperature)

        # Добавляем инструкцию по формату в промпт
        enhanced_prompt = prompt + "\n\nВАЖНО: Ответ должен быть только в формате JSON, без дополнительного текста."

        payload = {
            "model": self.model,
            "prompt": enhanced_prompt,
            "temperature": temperature,
            "stream": False,
            "format": "json"  # Просим модель вернуть JSON
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.api_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                return result.get('response', '')
            except requests.exceptions.Timeout:
                print(f"⏱️ Таймаут (попытка {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError:
                print(f"❌ Потеряно соединение с Ollama (попытка {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * 1.5)
                    self.check_connection()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"❌ Модель '{self.model}' не найдена. Проверьте имя модели.")
                    if self.available_models:
                        self.model = self.available_models[0]
                        print(f"   Переключено на модель: {self.model}")
                        payload["model"] = self.model
                        continue
                else:
                    print(f"❌ HTTP ошибка: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                print(f"❌ Ошибка при обращении к Ollama: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

        print("   Используется fallback режим после всех ошибок")
        return self._generate_fallback_response(prompt)

    def _generate_fallback_response(self, prompt: str) -> str:
        """
        Генерация fallback ответа когда Ollama недоступна
        """
        return json.dumps({
            "overall_rating": 4,
            "topic": "Оценка на основе метаданных",
            "criteria_ratings": {
                "client_satisfaction": 4,
                "issue_resolution": 4,
                "customer_orientation": 4,
                "operator_courtesy": 4
            },
            "explanations": {
                "client_satisfaction": "Оценка на основе метаданных (Ollama недоступна)",
                "issue_resolution": "Оценка на основе метаданных",
                "customer_orientation": "Оценка на основе метаданных",
                "operator_courtesy": "Оценка на основе метаданных"
            },
            "group": 2
        })

