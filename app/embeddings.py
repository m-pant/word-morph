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
        self.embeddings_matrix: Optional[np.ndarray] = None  # Кэшированная матрица эмбеддингов
        self.words_list: Optional[List[str]] = None  # Список слов в том же порядке что и матрица

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

            # Создаем кэшированную матрицу эмбеддингов для быстрого поиска
            self._build_embeddings_matrix()
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели Navec: {e}")
            raise

    def _build_embeddings_matrix(self):
        """Построение матрицы эмбеддингов для векторизованных операций"""
        logger.info("Создание матрицы эмбеддингов для ускорения поиска...")

        # Создаем список слов и матрицу эмбеддингов
        self.words_list = list(self.model.vocab.words)
        embeddings = np.array([self.model[word] for word in self.words_list])

        # Предварительная нормализация для косинусного сходства
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.embeddings_matrix = embeddings / norms

        logger.info(f"Матрица готова: {len(self.words_list)} слов, размер {self.embeddings_matrix.shape}")

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
        Поиск семантически близких слов (векторизованная версия)

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
        if self.model is None or self.embeddings_matrix is None:
            raise RuntimeError("Модель не загружена")

        # Режим случайных слов
        if random_mode:
            return self._get_random_words(count)

        # Получаем эмбеддинг исходного слова
        word_embedding = self.get_embedding(word)
        if word_embedding is None:
            raise ValueError(f"Слово '{word}' не найдено в словаре эмбеддингов")

        # Нормализуем вектор запроса
        word_norm = word_embedding / np.linalg.norm(word_embedding)

        # ВЕКТОРИЗОВАННОЕ вычисление косинусного сходства со всеми словами
        # Матричное умножение: (500K x 300) @ (300 x 1) = (500K x 1)
        similarities = np.dot(self.embeddings_matrix, word_norm)

        # Находим индекс исходного слова для исключения
        word_lower = word.lower()
        try:
            word_idx = self.words_list.index(word_lower)
            similarities[word_idx] = -1  # Исключаем само слово
        except ValueError:
            pass  # Слово не в списке, ничего не делаем

        # Исключаем технические токены
        for tech_token in ['<pad>', '<unk>', '<s>', '</s>']:
            try:
                tech_idx = self.words_list.index(tech_token)
                similarities[tech_idx] = -1
            except ValueError:
                pass

        # Получаем top-k индексов с учетом stride и фильтрации
        # Берем больше кандидатов для применения фильтров
        candidate_count = min(count * 20, len(similarities))

        # Частичная сортировка (быстрее полной) - находим top-k
        top_indices = np.argpartition(similarities, -candidate_count)[-candidate_count:]

        # Сортируем только top-k элементов
        top_indices = top_indices[np.argsort(similarities[top_indices])][::-1]

        # Формируем список кандидатов
        candidates = [
            (self.words_list[idx], float(similarities[idx]))
            for idx in top_indices
        ]

        # Применяем stride и фильтрацию похожих слов
        result = self._apply_stride_and_filter(
            candidates,
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
