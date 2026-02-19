"""Парсер для загрузки диалогов из Excel"""

import os
import pandas as pd
from typing import List, Optional
from models.dialog_models import Dialog, DialogMetadata


class ExcelParser:
    """Парсер для загрузки диалогов из Excel"""

    def __init__(self, file_path: str):
        """
        Args:
            file_path: путь к Excel файлу с данными диалогов
        """
        self.file_path = file_path
        self.dialogs: List[Dialog] = []

    def validate_file(self) -> bool:
        """Проверка существования файла"""
        if not os.path.exists(self.file_path):
            print(f"❌ Файл {self.file_path} не найден")
            return False
        return True

    def load_dialogs(self, limit: Optional[int] = None) -> List[Dialog]:
        """
        Загрузка диалогов из Excel файла

        Args:
            limit: ограничение на количество загружаемых диалогов

        Returns:
            List[Dialog]: список загруженных диалогов
        """
        if not self.validate_file():
            return []

        try:
            # Пробуем разные движки для чтения Excel
            try:
                df = pd.read_excel(self.file_path, engine='openpyxl')
            except:
                df = pd.read_excel(self.file_path, engine='xlrd')

            print(f"✅ Загружено {len(df)} строк из файла {self.file_path}")

            for idx, row in df.iterrows():
                if limit and idx >= limit:
                    break

                metadata = DialogMetadata.from_dataframe_row(row)

                # Создаем диалог (без истории сообщений, т.к. в файле только метаданные)
                dialog = Dialog(
                    id=metadata.dialog_id,
                    metadata=metadata,
                    messages=[]
                )

                self.dialogs.append(dialog)

            return self.dialogs

        except Exception as e:
            print(f"❌ Ошибка при загрузке файла {self.file_path}: {e}")
            return []

    def get_statistics(self) -> dict:
        """Получить статистику по загруженным диалогам"""
        if not self.dialogs:
            return {}

        stats = {
            'total': len(self.dialogs),
            'with_rating': 0,
            'avg_duration': 0,
            'categories': {},
            'topics': {}
        }

        total_duration = 0

        for dialog in self.dialogs:
            if dialog.metadata.client_rating:
                stats['with_rating'] += 1

            total_duration += dialog.metadata.dialog_duration

            cat = dialog.metadata.category
            if cat:
                stats['categories'][cat] = stats['categories'].get(cat, 0) + 1

            topic = dialog.metadata.topic
            if topic:
                stats['topics'][topic] = stats['topics'].get(topic, 0) + 1

        if stats['total'] > 0:
            stats['avg_duration'] = total_duration / stats['total'] / 60  # в минутах

        return stats