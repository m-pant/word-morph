"""
Вспомогательные функции
"""
import logging
from typing import Dict, Any, List, Optional
import pymorphy2
from wordfreq import zipf_frequency

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Глобальный экземпляр морфологического анализатора
morph = pymorphy2.MorphAnalyzer()

# Маппинг частей речи на коды pymorphy2
POS_MAPPING = {
    'noun': 'NOUN',        # существительное
    'adjf': 'ADJF',        # прилагательное (полное)
    'adjs': 'ADJS',        # прилагательное (краткое)
    'verb': 'VERB',        # глагол (личная форма)
    'infn': 'INFN',        # глагол (инфинитив)
    'prtf': 'PRTF',        # причастие (полное)
    'prts': 'PRTS',        # причастие (краткое)
    'grnd': 'GRND',        # деепричастие
    'numr': 'NUMR',        # числительное
    'advb': 'ADVB',        # наречие
    'npro': 'NPRO',        # местоимение-существительное
    'pred': 'PRED',        # предикатив
    'prep': 'PREP',        # предлог
    'conj': 'CONJ',        # союз
    'prcl': 'PRCL',        # частица
    'intj': 'INTJ',        # междометие
}

# Упрощенные группы частей речи
POS_GROUPS = {
    'adjective': ['ADJF', 'ADJS'],                    # все прилагательные
    'verb_all': ['VERB', 'INFN', 'PRTF', 'PRTS', 'GRND'],  # все глагольные формы
    'participle': ['PRTF', 'PRTS'],                   # причастия
}


def normalize_word(word: str) -> str:
    """
    Приведение слова к начальной форме (именительный падеж единственного числа)

    Args:
        word: Слово для нормализации

    Returns:
        Нормализованное слово
    """
    parsed = morph.parse(word.lower())
    if parsed:
        return parsed[0].normal_form
    return word.lower()


def get_word_pos(word: str) -> Optional[str]:
    """
    Определение части речи слова

    Args:
        word: Слово для анализа

    Returns:
        Код части речи (NOUN, VERB, и т.д.) или None
    """
    parsed = morph.parse(word.lower())
    if parsed:
        return parsed[0].tag.POS
    return None


def filter_words_by_pos(words: List[str], pos_filter: Optional[str]) -> List[str]:
    """
    Фильтрация слов по части речи

    Args:
        words: Список слов для фильтрации
        pos_filter: Фильтр части речи (noun, verb, adjf, и т.д.) или None

    Returns:
        Отфильтрованный список слов
    """
    if not pos_filter or pos_filter == 'all':
        return words

    # Определяем целевые POS коды
    target_pos_codes = []

    # Проверяем, это группа или отдельная часть речи
    if pos_filter in POS_GROUPS:
        target_pos_codes = POS_GROUPS[pos_filter]
    elif pos_filter in POS_MAPPING:
        target_pos_codes = [POS_MAPPING[pos_filter]]
    else:
        # Если передан напрямую код pymorphy2 (например, NOUN)
        target_pos_codes = [pos_filter.upper()]

    # Фильтруем слова
    filtered = []
    for word in words:
        word_pos = get_word_pos(word)
        if word_pos in target_pos_codes:
            filtered.append(word)

    return filtered


def get_word_frequency(word: str) -> float:
    """
    Получение частотности слова по шкале Zipf (0-8)
    
    Args:
        word: Слово для проверки
        
    Returns:
        Частотность (float)
    """
    return zipf_frequency(word, 'ru')


def is_word_appropriate_for_age(word: str, age: Optional[int]) -> bool:
    """
    Проверка слова на соответствие возрасту на основе частотности
    
    Args:
        word: Слово для проверки
        age: Возраст пользователя (None = без ограничений)
        
    Returns:
        True, если слово подходит
    """
    if age is None:
        return True
        
    freq = get_word_frequency(word)
    
    # Логика фильтрации по возрасту
    if age < 7:
        # Для дошкольников: только очень частые слова
        return freq >= 5.0
    elif age < 12:
        # Для младших школьников: частые и средние
        return freq >= 4.0
    elif age < 16:
        # Для подростков: допускаем более редкие
        return freq >= 3.0
    else:
        # Для взрослых и старших подростков: почти все слова
        # Отсекаем только совсем редкий мусор/опечатки
        return freq >= 1.5


def validate_parameters(
    word: str,
    count: int,
    skip_letters: int,
    letter_type: str,
    stride: int = 0,
    similarity_threshold: float = 0.0,
    pos_filter: Optional[str] = None
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
        pos_filter: Фильтр по части речи

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

    # Проверка pos_filter
    if pos_filter and pos_filter != 'all':
        valid_pos = list(POS_MAPPING.keys()) + list(POS_GROUPS.keys()) + ['all']
        if pos_filter not in valid_pos:
            raise ValueError(
                f"Параметр 'pos_filter' должен быть одним из: {', '.join(sorted(valid_pos))}"
            )

    return {
        'word': word.strip(),
        'count': count,
        'skip_letters': skip_letters,
        'letter_type': letter_type,
        'stride': stride,
        'similarity_threshold': similarity_threshold,
        'pos_filter': pos_filter
    }
