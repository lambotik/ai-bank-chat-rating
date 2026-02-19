#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Главный модуль для запуска системы оценки качества обслуживания банка
"""

import os
import sys
from typing import Optional

# Добавляем путь к проекту в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from services import OllamaClient, PromptTemplate, GroupClassifier, RatingCalculator
from parsers import ExcelParser
from core import DialogRatingSystem
from utils import check_ollama_process, get_available_models


def print_header():
    """Вывод заголовка программы"""
    print("=" * 70)
    print("🚀 СИСТЕМА ОЦЕНКИ КАЧЕСТВА ОБСЛУЖИВАНИЯ БАНКА")
    print("=" * 70)


def print_separator():
    """Вывод разделителя"""
    print("-" * 70)


def get_user_input(prompt: str, default: str = "") -> str:
    """Получение ввода от пользователя"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def main():
    """Основная функция"""
    print_header()

    # Проверяем наличие Ollama
    if check_ollama_process():
        print("✅ Процесс Ollama найден")
        available_models = get_available_models()
        if available_models:
            print(f"📚 Доступные модели: {', '.join(available_models)}")
    else:
        print("⚠️ Процесс Ollama не найден")
        print("   Для работы с реальной моделью запустите: ollama serve")
        print("   Программа будет работать в автономном режиме\n")
        available_models = []

    print_separator()

    # Настройка модели
    use_default_model = get_user_input("Использовать модель по умолчанию? (y/n)", "y")

    if use_default_model.lower() == 'y':
        model = settings.ollama.model
    else:
        if available_models:
            print(f"Доступные модели: {', '.join(available_models)}")
            model = get_user_input("Введите название модели", available_models[0])
        else:
            model = get_user_input("Введите название модели", "phi:2.7b")

    # Путь к файлу
    default_path = os.path.join(os.getcwd(), "dialogs.xlsx")
    file_path = get_user_input("📁 Введите путь к Excel файлу с диалогами", default_path)

    # Количество диалогов
    limit_input = get_user_input("📊 Сколько диалогов оценить? (Enter для всех)", "")
    limit = int(limit_input) if limit_input.isdigit() else None

    print_separator()

    # Создаем компоненты системы
    ollama = OllamaClient(
        base_url=settings.ollama.base_url,
        model=model,
        timeout=settings.ollama.timeout
    )

    prompt = PromptTemplate()
    classifier = GroupClassifier()
    calculator = RatingCalculator()

    # Создаем систему оценки
    system = DialogRatingSystem(ollama, prompt, classifier, calculator)

    # Загружаем диалоги
    parser = ExcelParser(file_path)
    dialogs = parser.load_dialogs(limit=limit)

    if not dialogs:
        print("❌ Не удалось загрузить диалоги. Проверьте путь к файлу.")
        return 1

    # Показываем статистику загруженных диалогов
    stats = parser.get_statistics()
    print(f"\n✅ Загружено {stats['total']} диалогов")
    print(f"📊 Средняя длительность: {stats['avg_duration']:.1f} минут")
    print(f"📊 Диалогов с оценкой: {stats['with_rating']}")

    print_separator()
    print("🔄 Начинаем оценку диалогов...\n")

    # Оцениваем диалоги
    results = system.rate_dialogs(dialogs)

    if not results:
        print("❌ Не удалось получить результаты оценки")
        return 1

    print_separator()
    print("💾 Сохраняем результаты...")

    # Экспортируем результаты
    system.export_results(settings.output_json, "json")
    system.export_results(settings.output_csv, "csv")

    # Выводим статистику
    result_stats = system.get_statistics()

    print_separator()
    print("📈 СТАТИСТИКА ОЦЕНОК")
    print_separator()

    print(f"📊 Средняя оценка: {result_stats['avg_rating']:.2f}")

    print("\n📊 Распределение по группам:")
    for group, count in sorted(result_stats['groups'].items()):
        percentage = count / result_stats['total'] * 100
        print(f"   Группа {group}: {count} диалогов ({percentage:.1f}%)")

    print("\n📊 Распределение по оценкам:")
    for rating in range(1, 6):
        count = result_stats['ratings'].get(rating, 0)
        percentage = count / result_stats['total'] * 100
        bar = "█" * int(percentage / 5)
        print(f"   Оценка {rating}: {count:2d} ({percentage:4.1f}%) {bar}")

    print_separator()
    print("✅ Обработка завершена!")
    print(f"📁 Результаты сохранены в: {settings.output_json} и {settings.output_csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())