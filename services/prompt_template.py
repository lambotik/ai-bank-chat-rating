"""Управление шаблонами промптов"""

from typing import Optional, Dict, Any
import json


class PromptTemplate:
    """Класс для управления промптами"""

    DEFAULT_TEMPLATE = """Ты — система оценки качества обслуживания банка. Проанализируй историю чата между клиентом и службой поддержки.

Данные диалога:
ID: {dialog_id}
Клиент: {client_name}
Категория: {category}
Тематика: {topic}
Подтематика: {subtopic}
Оценка клиента: {client_rating}

История чата:
{messages}

Необходимо оценить:
1. Вопрос клиента был полностью или частично решён?
2. Было ли общение понятным и полезным?
3. Сохранялась ли вежливость и профессионализм?
4. Насколько ответы были релевантные и точны?

Критерии оценки:
- Оценка "5": проблема полностью решена быстро и вежливо, даны точные инструкции, клиент благодарит
- Оценка "4": проблема решена, но были небольшие заминки или общие ответы
- Оценка "3": частичное решение или не очень удобное общение
- Оценка "2": не решено, но попытки были, медленная реакция
- Оценка "1": игнор, некорректные ответы, проблема не решена

Учитывай:
- Время ответа (целевой AHT - 12 минут)
- Количество сообщений
- Эмоциональную окраску (спасибо, восклицательные знаки, жалобы)
- Переводы на оператора

Определи группу диалога на основе ключевых слов:
Группа 1: Обращение зарегистрировано, Заблокировали, Арест, ФНС, Страхование, СБП, IOS, APPLE и др.
Группа 3: Доли, Перепланировк, 115-ФЗ, 161-ФЗ, Выход из состава заемщиков
Группа 2: остальные

Ответ представь строго в формате JSON:
{{
    "overall_rating": integer,
    "topic": "string",
    "criteria_ratings": {{
        "client_satisfaction": integer,
        "issue_resolution": integer,
        "customer_orientation": integer,
        "operator_courtesy": integer
    }},
    "explanations": {{
        "client_satisfaction": "string",
        "issue_resolution": "string",
        "customer_orientation": "string",
        "operator_courtesy": "string"
    }},
    "group": integer
}}"""

    def __init__(self, template_path: Optional[str] = None):
        self.template = self.DEFAULT_TEMPLATE
        if template_path:
            self.load_from_file(template_path)

    def load_from_file(self, path: str) -> bool:
        """Загрузка шаблона из файла"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.template = f.read()
            return True
        except Exception as e:
            print(f"Ошибка загрузки шаблона из {path}: {e}")
            return False

    def save_to_file(self, path: str) -> bool:
        """Сохранение шаблона в файл"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.template)
            return True
        except Exception as e:
            print(f"Ошибка сохранения шаблона в {path}: {e}")
            return False

    def format(self, **kwargs) -> str:
        """Форматирование шаблона с данными"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            print(f"Ошибка форматирования: отсутствует ключ {e}")
            # Возвращаем шаблон без форматирования в случае ошибки
            return self.template