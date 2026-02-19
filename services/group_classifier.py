"""Классификатор групп диалогов"""

from models.dialog_models import GroupEnum


class GroupClassifier:
    """Классификатор групп диалогов на основе ключевых слов"""

    GROUP_1_KEYWORDS = [
        'Обращение зарегистрировано', 'Обращению', 'Обращение', 'Обращения',
        'Заблокировали', 'Арест', 'ФНС', 'Пошлина', 'Возврат', 'ПОЛИС',
        'Страхование', 'МВД', 'PUSH-уведомлений', 'СБП', 'Активация', 'IOS',
        'APPLE', 'Смс не работает', 'Аккредитив', 'Эскроу'
    ]

    GROUP_3_KEYWORDS = [
        'Доли', 'доли', 'долей', 'Доля', 'доля', 'Перепланировк',
        '115', '161', '115фз', '115-фз', '161фз', '161-фз', '115.2',
        'Выход из состава заемщиков', '115 федерального закона'
    ]

    @classmethod
    def classify(cls, text: str) -> GroupEnum:
        """
        Определение группы диалога на основе текста

        Args:
            text: текст диалога для анализа

        Returns:
            GroupEnum: группа диалога
        """
        if not text:
            return GroupEnum.GROUP_2

        text_lower = text.lower()

        # Проверка на группу 1
        for keyword in cls.GROUP_1_KEYWORDS:
            if keyword.lower() in text_lower:
                return GroupEnum.GROUP_1

        # Проверка на группу 3
        for keyword in cls.GROUP_3_KEYWORDS:
            if keyword.lower() in text_lower:
                return GroupEnum.GROUP_3

        return GroupEnum.GROUP_2

    @classmethod
    def classify_from_metadata(cls, category: str, topic: str, subtopic: str) -> GroupEnum:
        """Классификация на основе метаданных"""
        combined = f"{category} {topic} {subtopic}"
        return cls.classify(combined)