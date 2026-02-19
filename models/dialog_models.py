"""Модели данных для диалогов"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import pandas as pd


class RatingEnum(Enum):
    """Перечисление возможных оценок"""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class GroupEnum(Enum):
    """Группы диалогов на основе ключевых слов"""
    GROUP_1 = 1
    GROUP_2 = 2
    GROUP_3 = 3


@dataclass
class DialogMetadata:
    """Метаданные диалога из Excel файла"""
    dialog_id: str
    client_id: str
    client_name: str
    client_type: str
    channel: str
    operator_name: str
    start_time: str
    first_response_time: str
    dialog_duration: int
    dialog_duration_with_operator: int
    avg_response_time_operator: int
    client_rating: Optional[int]
    category: str
    topic: str
    subtopic: str
    phone: Optional[str]
    email: Optional[str]

    @classmethod
    def from_dataframe_row(cls, row: pd.Series) -> 'DialogMetadata':
        """Создание объекта из строки DataFrame"""
        return cls(
            dialog_id=row.get('id диалога', ''),
            client_id=row.get('id клиента', ''),
            client_name=row.get('ФИО клиента', ''),
            client_type=row.get('Тип клиента', ''),
            channel=row.get('Название канала', ''),
            operator_name=row.get('ФИО оператора', '').replace('<br>', ', '),
            start_time=row.get('Время поступления обращения в чат', ''),
            first_response_time=row.get('Время первого ответа оператора', ''),
            dialog_duration=row.get('Длительность диалога (сек)', 0),
            dialog_duration_with_operator=row.get('Длительность диалога с оператором (сек)', 0),
            avg_response_time_operator=row.get('Среднее время ответа оператора (сек)', 0),
            client_rating=row.get('Оценка', None),
            category=row.get('Категория', ''),
            topic=row.get('Тематика', ''),
            subtopic=row.get('Подтематика', ''),
            phone=row.get('Телефон', None),
            email=row.get('E-mail', None)
        )


@dataclass
class DialogMessage:
    """Модель сообщения в диалоге"""
    sender: str  # 'client', 'bot', 'operator'
    text: str
    timestamp: Optional[str] = None


@dataclass
class Dialog:
    """Модель диалога"""
    id: str
    metadata: DialogMetadata
    messages: List[DialogMessage] = field(default_factory=list)
    operator_transfers: List[Dict] = field(default_factory=list)


@dataclass
class RatingResult:
    """Результат оценки диалога"""
    overall_rating: int
    topic: str
    criteria_ratings: Dict[str, int]
    explanations: Dict[str, str]
    group: int
    dialog_id: str = ""