"""
Модуль для работы с векторными эмбеддингами Navec
"""
import logging
import os
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

    def find_similar_words(self, word: str, count: int = 10) -> List[Tuple[str, float]]:
        """
        Поиск семантически близких слов

        Args:
            word: Исходное слово
            count: Количество слов для возврата

        Returns:
            Список кортежей (слово, сходство)

        Raises:
            ValueError: Если слово не найдено в словаре
        """
        if self.model is None:
            raise RuntimeError("Модель не загружена")

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

        # Сортируем по убыванию сходства и берем топ-N
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:count]

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
