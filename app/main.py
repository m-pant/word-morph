"""
FastAPI приложение для поиска семантически близких слов с трансформациями
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.embeddings import embeddings_service
from app.transformations import apply_transformations
from app.utils import validate_parameters

logger = logging.getLogger(__name__)


# Модели Pydantic для ответов
class TransformationsInfo(BaseModel):
    """Информация о примененных трансформациях"""
    shuffle_letters: bool = Field(default=False)
    skip_letters: int = Field(default=0)
    show_skipped: bool = Field(default=False)
    add_errors: bool = Field(default=False)
    letter_type: str = Field(default='all')
    preserve_first: bool = Field(default=False)
    preserve_last: bool = Field(default=False)


class QueryInfo(BaseModel):
    """Информация о запросе"""
    word: str
    count: int
    stride: int = Field(default=0)
    random_mode: bool = Field(default=False)
    similarity_threshold: float = Field(default=0.0)
    transformations: TransformationsInfo


class SuccessResponse(BaseModel):
    """Успешный ответ"""
    status: str = Field(default='success')
    query: QueryInfo
    results: list[str]


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    status: str = Field(default='error')
    error: str
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Загрузка модели при старте
    logger.info("Запуск приложения...")
    try:
        embeddings_service.load_model()
        logger.info("Приложение готово к работе")
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        raise

    yield

    # Очистка ресурсов при завершении
    logger.info("Завершение работы приложения...")


# Создание приложения FastAPI
app = FastAPI(
    title="Word Morph API",
    description="API для поиска семантически близких слов с трансформациями",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint для мониторинга"""
    return {"status": "healthy"}


@app.get("/api/words", response_model=SuccessResponse)
async def get_similar_words(
    word: str = Query(..., description="Исходное слово для поиска"),
    count: int = Query(10, ge=1, le=100, description="Количество возвращаемых слов"),
    stride: int = Query(0, ge=0, description="Шаг выборки слов (0=последовательно, 1=через одно)"),
    random_mode: bool = Query(False, description="Вернуть случайные слова вместо семантически близких"),
    similarity_threshold: float = Query(0.0, ge=0.0, le=1.0, description="Порог текстовой схожести слов (0.0-1.0)"),
    shuffle_letters: bool = Query(False, description="Перестановка букв в словах"),
    skip_letters: int = Query(0, ge=0, description="Количество букв для пропуска"),
    show_skipped: bool = Query(False, description="Показывать пропущенные буквы как _"),
    add_errors: bool = Query(False, description="Добавлять случайные ошибки в слова"),
    letter_type: str = Query('all', description="Тип букв: all, vowels, consonants"),
    preserve_first: bool = Query(False, description="Не трогать первую букву"),
    preserve_last: bool = Query(False, description="Не трогать последнюю букву")
):
    """
    Получение списка семантически близких слов с применением трансформаций

    Args:
        word: Исходное слово для поиска
        count: Количество возвращаемых слов (по умолчанию: 10)
        stride: Шаг выборки (0=последовательно, 1=через одно, и т.д.)
        random_mode: Вернуть случайные слова вместо семантически близких
        similarity_threshold: Порог текстовой схожести для фильтрации (0.0-1.0)
        shuffle_letters: Перестановка букв в словах
        skip_letters: Количество букв для пропуска
        show_skipped: Показывать пропущенные буквы как _
        add_errors: Добавлять случайные ошибки
        letter_type: Тип букв для трансформаций (all/vowels/consonants)
        preserve_first: Не трогать первую букву
        preserve_last: Не трогать последнюю букву

    Returns:
        JSON с результатами поиска

    Raises:
        HTTPException: При ошибках валидации или поиска
    """
    try:
        # Валидация параметров
        validated = validate_parameters(
            word, count, skip_letters, letter_type, stride, similarity_threshold
        )

        # Поиск семантически близких слов или случайных слов
        similar_words_with_scores = embeddings_service.find_similar_words(
            validated['word'],
            validated['count'],
            stride=validated['stride'],
            random_mode=random_mode,
            similarity_threshold=validated['similarity_threshold']
        )

        # Извлекаем только слова (без оценок сходства)
        similar_words = [word for word, score in similar_words_with_scores]

        # Применяем трансформации
        transformed_words = apply_transformations(
            words=similar_words,
            shuffle_letters=shuffle_letters,
            skip_letters=skip_letters,
            show_skipped=show_skipped,
            add_errors=add_errors,
            letter_type=letter_type,
            preserve_first=preserve_first,
            preserve_last=preserve_last
        )

        # Формируем ответ
        response = SuccessResponse(
            query=QueryInfo(
                word=validated['word'],
                count=validated['count'],
                stride=validated['stride'],
                random_mode=random_mode,
                similarity_threshold=validated['similarity_threshold'],
                transformations=TransformationsInfo(
                    shuffle_letters=shuffle_letters,
                    skip_letters=skip_letters,
                    show_skipped=show_skipped,
                    add_errors=add_errors,
                    letter_type=letter_type,
                    preserve_first=preserve_first,
                    preserve_last=preserve_last
                )
            ),
            results=transformed_words
        )

        return response

    except ValueError as e:
        # Слово не найдено или невалидные параметры
        error_message = str(e)

        if "не найдено в словаре" in error_message:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error": "word_not_found",
                    "message": error_message
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error": "invalid_parameters",
                    "message": error_message
                }
            )

    except Exception as e:
        # Другие ошибки
        logger.error(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": "internal_error",
                "message": "Внутренняя ошибка сервера"
            }
        )


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
