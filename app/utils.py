"""
Вспомогательные функции
"""
import logging
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def validate_parameters(
    word: str,
    count: int,
    skip_letters: int,
    letter_type: str,
    stride: int = 0,
    similarity_threshold: float = 0.0
) -> Dict[str, Any]:
    """
    Валидация параметров запроса

    Args:
        word: Исходное слово
        count: Количество слов для возврата
        skip_letters: Количество букв для пропуска
        letter_type: Тип букв
        stride: Шаг выборки слов
        similarity_threshold: Порог схожести слов

    Returns:
        Словарь с результатом валидации

    Raises:
        ValueError: Если параметры невалидны
    """
    # Проверка слова
    if not word or not word.strip():
        raise ValueError("Параметр 'word' не может быть пустым")

    # Проверка count
    if count < 1:
        raise ValueError("Параметр 'count' должен быть положительным числом")

    if count > 100:
        raise ValueError("Параметр 'count' не может быть больше 100")

    # Проверка skip_letters
    if skip_letters < 0:
        raise ValueError("Параметр 'skip_letters' не может быть отрицательным")

    # Проверка stride
    if stride < 0:
        raise ValueError("Параметр 'stride' не может быть отрицательным")

    # Проверка similarity_threshold
    if similarity_threshold < 0.0 or similarity_threshold > 1.0:
        raise ValueError("Параметр 'similarity_threshold' должен быть в диапазоне 0.0-1.0")

    # Проверка letter_type
    valid_letter_types = ['all', 'vowels', 'consonants']
    if letter_type not in valid_letter_types:
        raise ValueError(
            f"Параметр 'letter_type' должен быть одним из: {', '.join(valid_letter_types)}"
        )

    return {
        'word': word.strip(),
        'count': count,
        'skip_letters': skip_letters,
        'letter_type': letter_type,
        'stride': stride,
        'similarity_threshold': similarity_threshold
    }
