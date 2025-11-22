"""
FastAPI приложение для поиска семантически близких слов с трансформациями
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.embeddings import embeddings_service
from app.transformations import apply_transformations, apply_global_skip
from app.utils import validate_parameters, filter_words_by_pos, normalize_word, is_word_appropriate_for_age

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
    global_skip: bool = Field(default=False)


class QueryInfo(BaseModel):
    """Информация о запросе"""
    word: str
    count: int
    stride: int = Field(default=0)
    random_mode: bool = Field(default=False)
    similarity_threshold: float = Field(default=0.0)
    pos_filter: Optional[str] = Field(default=None)
    normalize: bool = Field(default=False)
    phrase_length: int = Field(default=1)
    age: Optional[int] = Field(default=None)
    transformations: TransformationsInfo


class WordResult(BaseModel):
    """Результат с исходным и трансформированным словом"""
    original: str = Field(description="Исходное слово")
    transformed: str = Field(description="Трансформированное слово")


class SuccessResponse(BaseModel):
    """Успешный ответ"""
    status: str = Field(default='success')
    query: QueryInfo
    results: list[str]
    sources: Optional[list[WordResult]] = Field(default=None, description="Пары исходных и трансформированных слов")


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

# Монтирование статической директории
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse('static/index.html')



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
    pos_filter: Optional[str] = Query(None, description="Фильтр по части речи (noun, verb, adjective, и т.д.)"),
    normalize: bool = Query(False, description="Привести слова к начальной форме (именительный падеж ед.ч.)"),
    return_source: bool = Query(False, description="Возвращать исходные слова вместе с трансформированными"),
    shuffle_letters: bool = Query(False, description="Перестановка букв в словах"),
    skip_letters: int = Query(0, ge=0, description="Количество букв для пропуска"),
    show_skipped: bool = Query(False, description="Показывать пропущенные буквы как _"),
    add_errors: bool = Query(False, description="Добавлять случайные ошибки в слова"),
    letter_type: str = Query('all', description="Тип букв: all, vowels, consonants"),
    preserve_first: bool = Query(False, description="Не трогать первую букву"),
    preserve_last: bool = Query(False, description="Не трогать последнюю букву"),
    phrase_length: int = Query(1, ge=1, le=3, description="Длина словосочетания (1-3 слова)"),
    age: Optional[int] = Query(None, ge=0, description="Возраст пользователя для фильтрации (лет)"),
    global_skip: bool = Query(False, description="Применять пропуск букв глобально ко всей фразе")
):
    """
    Получение списка семантически близких слов с применением трансформаций

    Args:
        word: Исходное слово для поиска
        count: Количество возвращаемых слов (по умолчанию: 10)
        stride: Шаг выборки (0=последовательно, 1=через одно, и т.д.)
        random_mode: Вернуть случайные слова вместо семантически близких
        similarity_threshold: Порог текстовой схожести для фильтрации (0.0-1.0)
        pos_filter: Фильтр по части речи (noun, verb, adjective, и т.д.)
        normalize: Привести слова к начальной форме (именительный падеж ед.ч.)
        return_source: Возвращать исходные слова вместе с трансформированными
        shuffle_letters: Перестановка букв в словах
        skip_letters: Количество букв для пропуска
        show_skipped: Показывать пропущенные буквы как _
        add_errors: Добавлять случайные ошибки
        letter_type: Тип букв для трансформаций (all/vowels/consonants)
        preserve_first: Не трогать первую букву
        preserve_last: Не трогать последнюю букву
        phrase_length: Длина словосочетания (1-3 слова)
        age: Возраст пользователя для фильтрации
        global_skip: Применять пропуск букв глобально ко всей фразе

    Returns:
        JSON с результатами поиска

    Raises:
        HTTPException: При ошибках валидации или поиска
    """
    try:
        # Валидация параметров
        validated = validate_parameters(
            word, count, skip_letters, letter_type, stride, similarity_threshold, pos_filter
        )

        # Поиск семантически близких слов или случайных слов
        # Увеличиваем count для компенсации фильтрации по POS и дубликатов при нормализации
        search_count = validated['count']
        if pos_filter and pos_filter != 'all':
            search_count *= 5
        if normalize:
            search_count *= 3  # Компенсация за дубликаты после нормализации

        similar_words_with_scores = embeddings_service.find_similar_words(
            validated['word'],
            search_count,
            stride=validated['stride'],
            random_mode=random_mode,
            similarity_threshold=validated['similarity_threshold']
        )

        # Извлекаем только слова (без оценок сходства)
        similar_words = [word for word, score in similar_words_with_scores]

        # Применяем нормализацию (приведение к начальной форме)
        if normalize:
            similar_words = [normalize_word(word) for word in similar_words]
            # Удаляем дубликаты после нормализации, сохраняя порядок
            seen = set()
            unique_words = []
            for word in similar_words:
                if word not in seen:
                    seen.add(word)
                    unique_words.append(word)
            similar_words = unique_words

        # Применяем фильтрацию по части речи
        if pos_filter and pos_filter != 'all':
            similar_words = filter_words_by_pos(similar_words, pos_filter)
            # Ограничиваем до нужного количества после фильтрации
            similar_words = similar_words[:validated['count']]

        # Фильтрация по возрасту
        if age is not None:
            similar_words = [w for w in similar_words if is_word_appropriate_for_age(w, age)]
            # Если после фильтрации слов стало меньше count, это нормально, но можно было бы добрать.
            # Пока оставим как есть.
            
        # --- ЛОГИКА СЛОВОСОЧЕТАНИЙ ---
        if phrase_length > 1:
            phrases = []
            # Используем найденные слова как "ядра" (существительные)
            # И ищем к ним зависимые слова (прилагательные)
            
            for head_word in similar_words:
                if len(phrases) >= validated['count']:
                    break
                    
                # Ищем совместимые прилагательные
                adjectives = embeddings_service.find_compatible_words(
                    head_word, 
                    target_pos='adjective', 
                    count=5,
                    similarity_threshold=0.5
                )
                
                # Фильтруем прилагательные по возрасту тоже
                if age is not None:
                    adjectives = [w for w in adjectives if is_word_appropriate_for_age(w, age)]
                
                if adjectives:
                    # Берем лучшее прилагательное
                    adj1 = adjectives[0]
                    
                    if phrase_length == 3 and len(adjectives) > 1:
                        # Для длины 3 берем два прилагательных
                        adj2 = adjectives[1]
                        phrase = f"{adj1} {adj2} {head_word}"
                    else:
                        # Для длины 2 или если не нашли второго прилагательного
                        phrase = f"{adj1} {head_word}"
                        
                    phrases.append(phrase)
                else:
                    # Если не нашли пару, пропускаем или оставляем одно слово?
                    # По ТЗ нужны словосочетания. Пропускаем.
                    pass
            
            # Заменяем список слов на список фраз
            similar_words = phrases

        # Сохраняем исходные слова перед трансформацией (если нужно)
        original_words = similar_words.copy() if return_source else None

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
        
        # Применяем глобальный пропуск букв (если включен)
        if global_skip and skip_letters > 0:
            # Если включен глобальный пропуск, то локальный skip_letters уже сработал (или нет, зависит от логики)
            # Но по ТЗ: "поддрежка режима пропуска букв во всем словосочетании"
            # Значит, мы должны применить его ПОВЕРХ или ВМЕСТО локального.
            # Логичнее ВМЕСТО. Поэтому если global_skip=True, мы должны были передать skip_letters=0 в apply_transformations
            pass # Реализовано ниже через переопределение
            
        if global_skip and skip_letters > 0:
            # Переделываем трансформацию с нуля для глобального режима
            # 1. Берем исходные (или перемешанные) слова
            # 2. Собираем их во фразы
            # 3. Применяем глобальный скип
            
            # Сначала применим все трансформации КРОМЕ skip_letters
            base_transformed = apply_transformations(
                words=similar_words,
                shuffle_letters=shuffle_letters,
                skip_letters=0, # Отключаем локальный пропуск
                show_skipped=show_skipped,
                add_errors=add_errors,
                letter_type=letter_type,
                preserve_first=preserve_first,
                preserve_last=preserve_last
            )
            
            # Теперь применяем глобальный пропуск к каждой фразе
            final_words = []
            for word in base_transformed:
                # total_skips = skip_letters * количество слов (примерно)
                # Или просто skip_letters как общее число на фразу?
                # По ТЗ: "количество букв пропущенное в каждом слове" - это параметр.
                # "режима пропуска букв во всем словосочетании" - это другой режим.
                # Пусть global_skip означает, что skip_letters - это ОБЩЕЕ число пропусков на фразу.
                final_words.append(apply_global_skip(word, skip_letters, show_skipped))
            
            transformed_words = final_words

        # Создаем пары исходных и трансформированных слов (если запрошено)
        word_pairs = None
        if return_source:
            word_pairs = [
                WordResult(original=orig, transformed=trans)
                for orig, trans in zip(original_words, transformed_words)
            ]

        # Формируем ответ
        response = SuccessResponse(
            query=QueryInfo(
                word=validated['word'],
                count=validated['count'],
                stride=validated['stride'],
                random_mode=random_mode,
                similarity_threshold=validated['similarity_threshold'],
                pos_filter=pos_filter,
                normalize=normalize,
                phrase_length=phrase_length,
                age=age,
                transformations=TransformationsInfo(
                    shuffle_letters=shuffle_letters,
                    skip_letters=skip_letters,
                    show_skipped=show_skipped,
                    add_errors=add_errors,
                    letter_type=letter_type,
                    preserve_first=preserve_first,
                    preserve_last=preserve_last,
                    global_skip=global_skip
                )
            ),
            results=transformed_words,
            sources=word_pairs
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
