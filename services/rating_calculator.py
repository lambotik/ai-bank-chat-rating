"""Калькулятор для расчета оценок"""

from models.dialog_models import Dialog
from config.settings import settings


class RatingCalculator:
    """Калькулятор для расчета оценок на основе правил"""

    def __init__(self):
        self.target_aht = settings.rating.target_aht_seconds
        self.slow_response = settings.rating.slow_response_threshold

    def calculate_aht(self, dialog: Dialog) -> float:
        """
        Расчет Average Handling Time (среднее время обработки)

        Args:
            dialog: диалог для расчета

        Returns:
            float: время в минутах
        """
        return dialog.metadata.dialog_duration / 60.0

    def check_time_penalty(self, dialog: Dialog) -> bool:
        """
        Проверка, нужно ли снизить оценку из-за превышения времени

        Returns:
            True если время превышает лимит
        """
        return dialog.metadata.dialog_duration > self.target_aht

    def calculate_base_rating(self, dialog: Dialog) -> int:
        """
        Расчет базовой оценки на основе метаданных

        Args:
            dialog: диалог для оценки

        Returns:
            int: базовая оценка от 1 до 5
        """
        rating = dialog.metadata.client_rating

        if rating is None:
            # Если клиент не поставил оценку, используем правила
            rating = 4  # Базовая оценка по умолчанию

            # Штраф за долгое время ответа
            if dialog.metadata.avg_response_time_operator > self.slow_response:
                rating = max(1, rating - 1)

            # Штраф за общую длительность
            if self.check_time_penalty(dialog):
                rating = max(1, rating - 1)

        return rating

    def get_rating_description(self, rating: int) -> str:
        """Получить описание оценки"""
        descriptions = {
            5: "проблема полностью ясно решена быстро и вежливо",
            4: "проблема решена, но могли быть небольшие заминки",
            3: "частичное решение или не очень удобное общение",
            2: "не решено, но попытки были, медленная реакция",
            1: "игнор, некорректные ответы, проблема не решена"
        }
        return descriptions.get(rating, "оценка не определена")