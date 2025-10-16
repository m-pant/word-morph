"""
Модуль для применения трансформаций к словам
"""
import random
from typing import List, Set


# Определение гласных и согласных для русского языка
VOWELS = set('аеёиоуыэюяАЕЁИОУЫЭЮЯ')
CONSONANTS = set('бвгджзйклмнпрстфхцчшщъьБВГДЖЗЙКЛМНПРСТФХЦЧШЩЪЬ')

# Похожие буквы для добавления ошибок
SIMILAR_LETTERS = {
    'а': ['о', 'я'],
    'о': ['а', 'ё'],
    'е': ['ё', 'э'],
    'и': ['ы', 'й'],
    'у': ['ю'],
    'б': ['п', 'в'],
    'п': ['б'],
    'д': ['т'],
    'т': ['д'],
    'г': ['к'],
    'к': ['г'],
    'з': ['с'],
    'с': ['з'],
    'ж': ['ш'],
    'ш': ['щ', 'ж'],
    'в': ['ф', 'б'],
    'ф': ['в'],
}


class WordTransformer:
    """Класс для применения трансформаций к словам"""

    def __init__(
        self,
        letter_type: str = 'all',
        preserve_first: bool = False,
        preserve_last: bool = False
    ):
        """
        Args:
            letter_type: Тип букв для трансформаций ('all', 'vowels', 'consonants')
            preserve_first: Сохранять первую букву без изменений
            preserve_last: Сохранять последнюю букву без изменений
        """
        self.letter_type = letter_type
        self.preserve_first = preserve_first
        self.preserve_last = preserve_last

    def _get_transformable_indices(self, word: str) -> List[int]:
        """
        Получение индексов букв, которые можно трансформировать

        Args:
            word: Исходное слово

        Returns:
            Список индексов букв для трансформации
        """
        indices = []

        for i, char in enumerate(word):
            # Проверяем, нужно ли пропустить первую/последнюю букву
            if self.preserve_first and i == 0:
                continue
            if self.preserve_last and i == len(word) - 1:
                continue

            # Проверяем тип буквы
            if self.letter_type == 'vowels' and char in VOWELS:
                indices.append(i)
            elif self.letter_type == 'consonants' and char in CONSONANTS:
                indices.append(i)
            elif self.letter_type == 'all' and (char in VOWELS or char in CONSONANTS):
                indices.append(i)

        return indices

    def shuffle_letters(self, word: str) -> str:
        """
        Перестановка букв в слове

        Args:
            word: Исходное слово

        Returns:
            Слово с переставленными буквами
        """
        if len(word) < 3:
            return word

        word_list = list(word)
        indices = self._get_transformable_indices(word)

        if len(indices) < 2:
            return word

        # Получаем буквы для перестановки
        letters_to_shuffle = [word_list[i] for i in indices]

        # Перемешиваем буквы
        shuffled_letters = letters_to_shuffle.copy()
        random.shuffle(shuffled_letters)

        # Заменяем буквы в слове
        for idx, letter_pos in enumerate(indices):
            word_list[letter_pos] = shuffled_letters[idx]

        return ''.join(word_list)

    def skip_letters(self, word: str, skip_count: int, show_skipped: bool = False) -> str:
        """
        Пропуск (удаление) букв в слове

        Args:
            word: Исходное слово
            skip_count: Количество букв для пропуска
            show_skipped: Показывать пропущенные буквы как '_'

        Returns:
            Слово с пропущенными буквами
        """
        if len(word) < 3 or skip_count <= 0:
            return word

        indices = self._get_transformable_indices(word)

        if not indices:
            return word

        # Определяем, сколько букв можно пропустить
        actual_skip_count = min(skip_count, len(indices))

        # Выбираем случайные индексы для пропуска
        indices_to_skip = random.sample(indices, actual_skip_count)
        indices_to_skip_set = set(indices_to_skip)

        # Формируем результат
        result = []
        for i, char in enumerate(word):
            if i in indices_to_skip_set:
                if show_skipped:
                    result.append('_')
            else:
                result.append(char)

        return ''.join(result)

    def add_errors(self, word: str) -> str:
        """
        Добавление случайных ошибок в слово

        Args:
            word: Исходное слово

        Returns:
            Слово со случайными ошибками
        """
        if len(word) < 3:
            return word

        word_list = list(word)
        indices = self._get_transformable_indices(word)

        if not indices:
            return word

        # Определяем количество ошибок (1-2 в зависимости от длины слова)
        error_count = 1 if len(indices) <= 4 else min(2, len(indices))

        # Выбираем случайные позиции для ошибок
        error_positions = random.sample(indices, error_count)

        for pos in error_positions:
            original_char = word_list[pos]
            original_lower = original_char.lower()

            # Пытаемся заменить на похожую букву
            if original_lower in SIMILAR_LETTERS:
                similar = SIMILAR_LETTERS[original_lower]
                replacement = random.choice(similar)
            else:
                # Если нет похожих, выбираем случайную букву того же типа
                if original_lower in VOWELS:
                    replacement = random.choice(list(VOWELS))
                elif original_lower in CONSONANTS:
                    replacement = random.choice(list(CONSONANTS))
                else:
                    continue

            # Сохраняем регистр
            if original_char.isupper():
                replacement = replacement.upper()
            else:
                replacement = replacement.lower()

            word_list[pos] = replacement

        return ''.join(word_list)


def apply_transformations(
    words: List[str],
    shuffle_letters: bool = False,
    skip_letters: int = 0,
    show_skipped: bool = False,
    add_errors: bool = False,
    letter_type: str = 'all',
    preserve_first: bool = False,
    preserve_last: bool = False
) -> List[str]:
    """
    Применение трансформаций к списку слов

    Args:
        words: Список слов для трансформации
        shuffle_letters: Перестановка букв
        skip_letters: Количество букв для пропуска
        show_skipped: Показывать пропущенные буквы как '_'
        add_errors: Добавлять случайные ошибки
        letter_type: Тип букв ('all', 'vowels', 'consonants')
        preserve_first: Сохранять первую букву
        preserve_last: Сохранять последнюю букву

    Returns:
        Список трансформированных слов
    """
    transformer = WordTransformer(
        letter_type=letter_type,
        preserve_first=preserve_first,
        preserve_last=preserve_last
    )

    transformed_words = []

    for word in words:
        transformed = word

        # Применяем трансформации в порядке приоритета
        if shuffle_letters:
            transformed = transformer.shuffle_letters(transformed)

        if skip_letters > 0:
            transformed = transformer.skip_letters(transformed, skip_letters, show_skipped)

        if add_errors:
            transformed = transformer.add_errors(transformed)

        transformed_words.append(transformed)

    return transformed_words
