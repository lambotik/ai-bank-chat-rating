# Этот файл делает папку services Python-пакетом
from .ollama_client import OllamaClient
from .prompt_template import PromptTemplate
from .group_classifier import GroupClassifier
from .rating_calculator import RatingCalculator

__all__ = ['OllamaClient', 'PromptTemplate', 'GroupClassifier', 'RatingCalculator']