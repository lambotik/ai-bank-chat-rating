"""Основная система оценки диалогов"""

import json
import re
import time
from typing import List, Optional, Dict, Any
from models.dialog_models import Dialog, RatingResult
from services.ollama_client import OllamaClient
from services.prompt_template import PromptTemplate
from services.group_classifier import GroupClassifier
from services.rating_calculator import RatingCalculator
from config.settings import settings


class DialogRatingSystem:
    """Основной класс системы оценки диалогов"""

    def __init__(self,
                 ollama_client: OllamaClient,
                 prompt_template: PromptTemplate,
                 group_classifier: GroupClassifier,
                 rating_calculator: RatingCalculator):
        """
        Args:
            ollama_client: клиент для Ollama
            prompt_template: шаблон промпта
            group_classifier: классификатор групп
            rating_calculator: калькулятор оценок
        """
        self.ollama = ollama_client
        self.prompt_template = prompt_template
        self.classifier = group_classifier
        self.calculator = rating_calculator
        self.results: List[RatingResult] = []

    def prepare_messages_text(self, dialog: Dialog) -> str:
        """
        Подготовка текста сообщений для промпта

        Args:
            dialog: диалог для обработки

        Returns:
            str: отформатированный текст сообщений
        """
        if not dialog.messages:
            # Если нет истории сообщений, используем метаданные
            return f"""История сообщений отсутствует. Доступна следующая информация:
- Категория: {dialog.metadata.category}
- Тематика: {dialog.metadata.topic}
- Подтематика: {dialog.metadata.subtopic}
- Оператор: {dialog.metadata.operator_name}
- Длительность: {dialog.metadata.dialog_duration} сек
- Среднее время ответа: {dialog.metadata.avg_response_time_operator} сек
- Оценка клиента: {dialog.metadata.client_rating if dialog.metadata.client_rating else 'не указана'}"""

        messages_text = []
        for msg in dialog.messages:
            timestamp = f"[{msg.timestamp}] " if msg.timestamp else ""
            messages_text.append(f"{timestamp}{msg.sender}: {msg.text}")

        return "\n".join(messages_text)

    def prepare_prompt(self, dialog: Dialog) -> str:
        """
        Подготовка полного промпта для диалога

        Args:
            dialog: диалог для оценки

        Returns:
            str: готовый промпт
        """
        messages_text = self.prepare_messages_text(dialog)
        aht = self.calculator.calculate_aht(dialog)

        # Добавляем информацию о времени в промпт
        time_info = f"""
Метрики времени:
- Длительность диалога: {aht:.1f} минут
- Среднее время ответа оператора: {dialog.metadata.avg_response_time_operator} сек
- Превышение лимита {settings.rating.target_aht_minutes} минут: {'ДА' if self.calculator.check_time_penalty(dialog) else 'НЕТ'}
"""

        return self.prompt_template.format(
            dialog_id=dialog.id,
            client_name=dialog.metadata.client_name,
            category=dialog.metadata.category,
            topic=dialog.metadata.topic,
            subtopic=dialog.metadata.subtopic,
            client_rating=dialog.metadata.client_rating or "не указана",
            messages=messages_text + time_info
        )

    def clean_json_string(self, text: str) -> str:
        """
        Очистка JSON строки от недопустимых символов и маркдауна

        Args:
            text: сырой текст ответа

        Returns:
            str: очищенный текст
        """
        # Удаляем markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # Удаляем лишний текст до первого {
        first_brace = text.find('{')
        if first_brace > 0:
            text = text[first_brace:]

        # Удаляем лишний текст после последнего }
        last_brace = text.rfind('}')
        if last_brace > 0 and last_brace < len(text) - 1:
            text = text[:last_brace + 1]

        # Экранируем управляющие символы
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

        return text.strip()

    def extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Извлечение JSON из текста с возможными ошибками форматирования

        Args:
            text: текст для парсинга

        Returns:
            Optional[str]: найденный JSON или None
        """
        # Сначала пробуем найти JSON с помощью регулярного выражения
        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)

        if matches:
            # Берем самое длинное совпадение (скорее всего это полный JSON)
            best_match = max(matches, key=len)
            return best_match

        return None

    def parse_model_response(self, response: str, dialog_id: str = "") -> Optional[Dict[str, Any]]:
        """
        Улучшенный парсинг JSON ответа от модели

        Args:
            response: сырой ответ от модели
            dialog_id: ID диалога для логирования

        Returns:
            Optional[Dict]: распарсенный JSON или None
        """
        if not response:
            print(f"⚠️ [{dialog_id}] Пустой ответ от модели")
            return None

        # Очищаем ответ
        cleaned_response = self.clean_json_string(response)

        # Пробуем извлечь JSON
        json_str = self.extract_json_from_text(cleaned_response)

        if not json_str:
            print(f"⚠️ [{dialog_id}] Не удалось найти JSON в ответе")
            print(f"   Ответ: {response[:200]}...")
            return None

        # Пробуем распарсить JSON с разными стратегиями
        parsing_strategies = [
            lambda s: json.loads(s),  # Прямой парсинг
            lambda s: json.loads(s.replace("'", '"')),  # Замена кавычек
            lambda s: json.loads(re.sub(r',\s*}', '}', s)),  # Удаление лишних запятых
        ]

        for i, strategy in enumerate(parsing_strategies):
            try:
                result = strategy(json_str)
                # Проверяем наличие обязательных полей
                if self.validate_response_structure(result):
                    return result
                else:
                    print(f"⚠️ [{dialog_id}] Отсутствуют обязательные поля в JSON")
            except json.JSONDecodeError as e:
                if i == len(parsing_strategies) - 1:
                    print(f"⚠️ [{dialog_id}] Ошибка парсинга JSON: {e}")
                    print(f"   JSON: {json_str[:200]}...")

        return None

    def validate_response_structure(self, data: Dict) -> bool:
        """
        Проверка структуры ответа от модели

        Args:
            data: распарсенные данные

        Returns:
            bool: True если структура корректна
        """
        required_fields = ['overall_rating', 'criteria_ratings']
        criteria_fields = ['client_satisfaction', 'issue_resolution',
                          'customer_orientation', 'operator_courtesy']

        # Проверяем наличие обязательных полей
        for field in required_fields:
            if field not in data:
                return False

        # Проверяем структуру criteria_ratings
        if not isinstance(data.get('criteria_ratings'), dict):
            return False

        for field in criteria_fields:
            if field not in data['criteria_ratings']:
                data['criteria_ratings'][field] = 3  # Значение по умолчанию

        # Проверяем диапазон оценок
        if not 1 <= data['overall_rating'] <= 5:
            data['overall_rating'] = 3

        for field in criteria_fields:
            value = data['criteria_ratings'][field]
            if not 1 <= value <= 5:
                data['criteria_ratings'][field] = 3

        return True

    def create_fallback_result(self, dialog: Dialog) -> RatingResult:
        """
        Создание fallback результата на основе метаданных

        Args:
            dialog: диалог для оценки

        Returns:
            RatingResult: результат оценки
        """
        # Базовая оценка на основе метаданных
        base_rating = self.calculator.calculate_base_rating(dialog)

        # Определяем группу
        group_enum = self.classifier.classify_from_metadata(
            dialog.metadata.category,
            dialog.metadata.topic,
            dialog.metadata.subtopic
        )

        return RatingResult(
            overall_rating=base_rating,
            topic=dialog.metadata.topic,
            criteria_ratings={
                'client_satisfaction': base_rating,
                'issue_resolution': base_rating,
                'customer_orientation': base_rating,
                'operator_courtesy': base_rating
            },
            explanations={
                'client_satisfaction': f'Оценка на основе метаданных. {self.calculator.get_rating_description(base_rating)}',
                'issue_resolution': f'Оценка на основе категории: {dialog.metadata.category}',
                'customer_orientation': f'Время ответа: {dialog.metadata.avg_response_time_operator} сек',
                'operator_courtesy': f'Длительность диалога: {dialog.metadata.dialog_duration} сек'
            },
            group=group_enum.value,
            dialog_id=dialog.id
        )

    def rate_dialog(self, dialog: Dialog) -> Optional[RatingResult]:
        """
        Оценка одного диалога

        Args:
            dialog: диалог для оценки

        Returns:
            Optional[RatingResult]: результат оценки или None
        """
        prompt = self.prepare_prompt(dialog)
        response = self.ollama.generate(prompt)

        if not response:
            print(f"⚠️ [{dialog.id[:8]}] Не удалось получить ответ от модели, используем fallback")
            return self.create_fallback_result(dialog)

        parsed = self.parse_model_response(response, dialog.id[:8])
        if not parsed:
            print(f"⚠️ [{dialog.id[:8]}] Ошибка парсинга ответа, используем fallback")
            return self.create_fallback_result(dialog)

        # Используем классификатор для определения группы, если модель не определила
        group = parsed.get('group')
        if not group:
            group_enum = self.classifier.classify_from_metadata(
                dialog.metadata.category,
                dialog.metadata.topic,
                dialog.metadata.subtopic
            )
            group = group_enum.value

        result = RatingResult(
            overall_rating=parsed.get('overall_rating', 3),
            topic=parsed.get('topic', dialog.metadata.topic),
            criteria_ratings=parsed.get('criteria_ratings', {
                'client_satisfaction': 3,
                'issue_resolution': 3,
                'customer_orientation': 3,
                'operator_courtesy': 3
            }),
            explanations=parsed.get('explanations', {
                'client_satisfaction': 'Нет объяснения',
                'issue_resolution': 'Нет объяснения',
                'customer_orientation': 'Нет объяснения',
                'operator_courtesy': 'Нет объяснения'
            }),
            group=group,
            dialog_id=dialog.id
        )

        return result

    def rate_dialogs(self, dialogs: List[Dialog]) -> List[RatingResult]:
        """
        Оценка списка диалогов

        Args:
            dialogs: список диалогов для оценки

        Returns:
            List[RatingResult]: список результатов
        """
        self.results = []

        if not dialogs:
            print("⚠️ Нет диалогов для оценки")
            return []

        # Проверяем подключение к Ollama
        if not self.ollama.available:
            print("\n⚠️ Работа в автономном режиме (без Ollama)")
            print("   Оценки будут основаны на метаданных и правилах\n")

        for i, dialog in enumerate(dialogs):
            print(f"📊 Оценка диалога {i + 1}/{len(dialogs)}: {dialog.id[:8]}...")
            result = self.rate_dialog(dialog)
            if result:
                self.results.append(result)
                print(f"   ✅ Оценка: {result.overall_rating}, Группа: {result.group}")
            else:
                print(f"   ❌ Ошибка оценки диалога {dialog.id}")

            # Небольшая пауза между запросами
            if i < len(dialogs) - 1:
                time.sleep(0.5)

        return self.results

    def export_results(self, file_path: str, format: str = 'json') -> bool:
        """
        Экспорт результатов в файл

        Args:
            file_path: путь для сохранения
            format: формат ('json' или 'csv')

        Returns:
            bool: True если успешно
        """
        if not self.results:
            print("⚠️ Нет результатов для экспорта")
            return False

        try:
            if format == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([{
                        'dialog_id': r.dialog_id,
                        'overall_rating': r.overall_rating,
                        'topic': r.topic,
                        'group': r.group,
                        'criteria_ratings': r.criteria_ratings,
                        'explanations': r.explanations
                    } for r in self.results], f, ensure_ascii=False, indent=2)
                print(f"✅ Результаты сохранены в {file_path}")

            elif format == 'csv':
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['dialog_id', 'overall_rating', 'topic', 'group',
                                     'client_satisfaction', 'issue_resolution',
                                     'customer_orientation', 'operator_courtesy',
                                     'explanation_client', 'explanation_issue',
                                     'explanation_orientation', 'explanation_courtesy'])

                    for r in self.results:
                        writer.writerow([
                            r.dialog_id,
                            r.overall_rating,
                            r.topic,
                            r.group,
                            r.criteria_ratings['client_satisfaction'],
                            r.criteria_ratings['issue_resolution'],
                            r.criteria_ratings['customer_orientation'],
                            r.criteria_ratings['operator_courtesy'],
                            r.explanations['client_satisfaction'],
                            r.explanations['issue_resolution'],
                            r.explanations['customer_orientation'],
                            r.explanations['operator_courtesy']
                        ])
                print(f"✅ Результаты сохранены в {file_path}")

            return True

        except Exception as e:
            print(f"❌ Ошибка при сохранении результатов: {e}")
            return False

    def get_statistics(self) -> dict:
        """Получить статистику по оценкам"""
        if not self.results:
            return {}

        stats = {
            'total': len(self.results),
            'avg_rating': sum(r.overall_rating for r in self.results) / len(self.results),
            'groups': {},
            'ratings': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }

        for r in self.results:
            stats['groups'][r.group] = stats['groups'].get(r.group, 0) + 1
            stats['ratings'][r.overall_rating] = stats['ratings'].get(r.overall_rating, 0) + 1

        return stats