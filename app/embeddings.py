"""
Модуль для работы с векторными эмбеддингами Navec
"""
import logging
import os
import random
from typing import List, Optional, Tuple
import numpy as np
from navec import Navec

logger = logging.getLogger(__name__)

# URL модели Navec
NAVEC_MODEL_URL = 'https://storage.yandexcloud.net/natasha-navec/packs/navec_hudlit_v1_12B_500K_300d_100q.tar'
NAVEC_MODEL_NAME = 'navec_hudlit_v1_12B_500K_300d_100q.tar'


class EmbeddingsService:
    """Сервис для работы с векторными эмбеддингами"""

    def __init__(self):
        self.model: Optional[Navec] = None

    def load_model(self):
        """Загрузка модели Navec"""
        try:
            logger.info("Загрузка модели Navec...")

            # Проверяем, существует ли файл модели локально
            if not os.path.exists(NAVEC_MODEL_NAME):
                logger.info(f"Модель не найдена локально. Скачивание с {NAVEC_MODEL_URL}...")
                self._download_model()

            self.model = Navec.load(NAVEC_MODEL_NAME)
            logger.info("Модель Navec успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели Navec: {e}")
            raise

    def _download_model(self):
        """Скачивание модели Navec"""
        import urllib.request

        try:
            logger.info(f"Скачивание {NAVEC_MODEL_NAME}...")
            urllib.request.urlretrieve(NAVEC_MODEL_URL, NAVEC_MODEL_NAME)
            logger.info(f"Модель успешно скачана: {NAVEC_MODEL_NAME}")
        except Exception as e:
            logger.error(f"Ошибка при скачивании модели: {e}")
            raise

    def get_embedding(self, word: str) -> Optional[np.ndarray]:
        """
        Получение вектора эмбеддинга для слова

        Args:
            word: Слово для получения эмбеддинга

        Returns:
            Вектор эмбеддинга или None, если слово не найдено
        """
        if self.model is None:
            raise RuntimeError("Модель не загружена")

        word_lower = word.lower()
        if word_lower not in self.model:
            return None

        return self.model[word_lower]

    def find_similar_words(
        self,
        word: str,
        count: int = 10,
        stride: int = 0,
        random_mode: bool = False,
        similarity_threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Поиск семантически близких слов

        Args:
            word: Исходное слово
            count: Количество слов для возврата
            stride: Шаг выборки (0 = последовательно, 1 = через одно, и т.д.)
            random_mode: Если True, возвращает случайные слова из словаря
            similarity_threshold: Порог схожести слов (0.0-1.0). Слова с similarity >= threshold будут отфильтрованы

        Returns:
            Список кортежей (слово, сходство)

        Raises:
            ValueError: Если слово не найдено в словаре
        """
        if self.model is None:
            raise RuntimeError("Модель не загружена")

        # Режим случайных слов
        if random_mode:
            return self._get_random_words(count)

        # Получаем эмбеддинг исходного слова
        word_embedding = self.get_embedding(word)
        if word_embedding is None:
            raise ValueError(f"Слово '{word}' не найдено в словаре эмбеддингов")

        # Вычисляем косинусное сходство со всеми словами
        similarities = []
        word_lower = word.lower()

        for vocab_word in self.model.vocab.words:
            if vocab_word == word_lower:
                continue

            vocab_embedding = self.model[vocab_word]

            # Косинусное сходство
            similarity = self._cosine_similarity(word_embedding, vocab_embedding)
            similarities.append((vocab_word, similarity))

        # Сортируем по убыванию сходства
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Применяем stride и фильтрацию похожих слов
        result = self._apply_stride_and_filter(
            similarities,
            count,
            stride,
            similarity_threshold
        )

        return result

    def _get_random_words(self, count: int) -> List[Tuple[str, float]]:
        """
        Получение случайных слов из словаря

        Args:
            count: Количество слов

        Returns:
            Список кортежей (слово, 0.0)
        """
        if self.model is None:
            raise RuntimeError("Модель не загружена")

        all_words = list(self.model.vocab.words)
        selected_words = random.sample(all_words, min(count, len(all_words)))

        return [(word, 0.0) for word in selected_words]

    def _apply_stride_and_filter(
        self,
        similarities: List[Tuple[str, float]],
        count: int,
        stride: int,
        similarity_threshold: float
    ) -> List[Tuple[str, float]]:
        """
        Применение stride и фильтрации похожих слов

        Args:
            similarities: Отсортированный список (слово, сходство)
            count: Требуемое количество слов
            stride: Шаг выборки
            similarity_threshold: Порог схожести слов (доля совпадающих символов)

        Returns:
            Отфильтрованный список
        """
        result = []
        index = 0
        step = stride + 1  # Шаг 0 означает каждое слово, 1 - через одно и т.д.

        while len(result) < count and index < len(similarities):
            candidate_word, score = similarities[index]

            # Проверяем на схожесть с уже выбранными словами
            if self._is_word_acceptable(candidate_word, result, similarity_threshold):
                result.append((candidate_word, score))

            index += step

        # Если не хватило слов с учетом stride, добираем оставшиеся
        if len(result) < count:
            for i in range(len(similarities)):
                if len(result) >= count:
                    break

                candidate_word, score = similarities[i]

                # Пропускаем уже добавленные слова
                if any(candidate_word == w for w, _ in result):
                    continue

                # Проверяем на схожесть
                if self._is_word_acceptable(candidate_word, result, similarity_threshold):
                    result.append((candidate_word, score))

        return result[:count]

    def _is_word_acceptable(
        self,
        candidate: str,
        selected_words: List[Tuple[str, float]],
        threshold: float
    ) -> bool:
        """
        Проверка, приемлемо ли слово (не слишком похоже на уже выбранные)

        Args:
            candidate: Кандидат на добавление
            selected_words: Уже выбранные слова
            threshold: Порог схожести (0.0-1.0)

        Returns:
            True, если слово можно добавить
        """
        if threshold <= 0.0:
            return True

        for selected_word, _ in selected_words:
            similarity = self._calculate_string_similarity(candidate, selected_word)
            if similarity >= threshold:
                return False

        return True

    @staticmethod
    def _calculate_string_similarity(word1: str, word2: str) -> float:
        """
        Вычисление текстовой схожести слов (доля совпадающих символов)

        Args:
            word1: Первое слово
            word2: Второе слово

        Returns:
            Значение от 0.0 до 1.0
        """
        if not word1 or not word2:
            return 0.0

        # Считаем общие символы
        set1 = set(word1.lower())
        set2 = set(word2.lower())

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Вычисление косинусного сходства между двумя векторами

        Args:
            vec1: Первый вектор
            vec2: Второй вектор

        Returns:
            Значение косинусного сходства
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


# Глобальный экземпляр сервиса
embeddings_service = EmbeddingsService()
