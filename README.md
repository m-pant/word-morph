# Word Morph API

Веб-сервис для поиска семантически близких слов на основе векторных эмбеддингов с возможностью применения различных текстовых трансформаций.

## Возможности

- Поиск семантически близких слов на основе эмбеддингов Navec
- Фильтрация по части речи (существительные, прилагательные, глаголы и др.)
- Нормализация слов к начальной форме (именительный падеж единственного числа)
- Различные трансформации текста:
  - Перестановка букв
  - Пропуск букв (с возможностью отображения как `_`)
  - Добавление случайных ошибок
- Гибкая настройка трансформаций:
  - Работа только с гласными или согласными буквами
  - Сохранение первой/последней буквы
- REST API на базе FastAPI
- Контейнеризация с Docker

## Технологический стек

- Python 3.9+
- FastAPI
- Navec (русскоязычные word embeddings)
- pymorphy2 (морфологический анализ русского языка)
- Docker & Docker Compose

## Быстрый старт

### Требования

- Docker
- Docker Compose

### Запуск

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd word-morph
```

2. Запустите сервис с помощью Docker Compose:
```bash
docker-compose up --build
```

3. Сервис будет доступен по адресу: `http://localhost:8081`

4. Проверьте работоспособность:
```bash
curl http://localhost:8081/health
```

### Настройка порта

По умолчанию сервис использует порт 8081. Чтобы изменить порт, создайте файл `.env`:

```bash
PORT=9000
```

Или задайте переменную окружения:

```bash
PORT=9000 docker-compose up
```

### Важно: Использование кириллицы в URL

При работе с кириллическими параметрами в curl необходимо использовать правильное URL-кодирование:

```bash
# Правильно - с автоматическим кодированием
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=мебель" \
  --data-urlencode "count=3"

# Неправильно - приведет к ошибке "Invalid HTTP request"
curl "http://localhost:8081/api/words?word=мебель&count=3"
```

## API Документация

### Endpoints

#### GET /health
Health check endpoint для мониторинга состояния сервиса.

**Ответ:**
```json
{
  "status": "healthy"
}
```

#### GET /api/words
Получение списка семантически близких слов с применением трансформаций.

**Параметры запроса:**

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|--------------|--------------|----------|
| `word` | string | Да | - | Исходное слово для поиска |
| `count` | integer | Нет | 10 | Количество возвращаемых слов (1-100) |
| `stride` | integer | Нет | 0 | Шаг выборки слов (0=последовательно, 1=через одно, 2=через два) |
| `random_mode` | boolean | Нет | false | Вернуть случайные слова вместо семантически близких |
| `similarity_threshold` | float | Нет | 0.0 | Порог текстовой схожести для фильтрации похожих слов (0.0-1.0) |
| `pos_filter` | string | Нет | - | Фильтр по части речи (noun, verb, adjective и др.) |
| `normalize` | boolean | Нет | false | Привести слова к начальной форме (именительный падеж ед.ч.) |
| `shuffle_letters` | boolean | Нет | false | Перестановка букв в словах |
| `skip_letters` | integer | Нет | 0 | Количество букв для пропуска |
| `show_skipped` | boolean | Нет | false | Показывать пропущенные буквы как `_` |
| `add_errors` | boolean | Нет | false | Добавлять случайные ошибки в слова |
| `letter_type` | string | Нет | all | Тип букв: `all`, `vowels`, `consonants` |
| `preserve_first` | boolean | Нет | false | Не трогать первую букву |
| `preserve_last` | boolean | Нет | false | Не трогать последнюю букву |

**Примеры запросов:**

1. **Базовый поиск:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=мебель" \
  --data-urlencode "count=3"
```

Ответ:
```json
{
  "status": "success",
  "query": {
    "word": "мебель",
    "count": 3,
    "transformations": {
      "shuffle_letters": false,
      "skip_letters": 0,
      "show_skipped": false,
      "add_errors": false,
      "letter_type": "all",
      "preserve_first": false,
      "preserve_last": false
    }
  },
  "results": ["ковры", "мебели", "стулья"]
}
```

2. **Перестановка букв:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=гроза" \
  --data-urlencode "count=5" \
  --data-urlencode "shuffle_letters=true"
```

3. **Пропуск букв с отображением:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=гроза" \
  --data-urlencode "count=5" \
  --data-urlencode "skip_letters=1" \
  --data-urlencode "show_skipped=true"
```

4. **Добавление ошибок только в согласные:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=погода" \
  --data-urlencode "count=5" \
  --data-urlencode "add_errors=true" \
  --data-urlencode "letter_type=consonants" \
  --data-urlencode "preserve_first=true"
```

5. **Комплексная трансформация:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=природа" \
  --data-urlencode "count=5" \
  --data-urlencode "shuffle_letters=true" \
  --data-urlencode "letter_type=vowels" \
  --data-urlencode "preserve_first=true" \
  --data-urlencode "preserve_last=true"
```

6. **Использование stride для разнообразия:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=воздух" \
  --data-urlencode "count=10" \
  --data-urlencode "stride=2"
```

7. **Фильтрация похожих слов:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=природа" \
  --data-urlencode "count=10" \
  --data-urlencode "similarity_threshold=0.6"
```

8. **Случайные слова из словаря:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=любое" \
  --data-urlencode "count=10" \
  --data-urlencode "random_mode=true"
```

9. **Фильтрация по части речи (существительные):**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=стул" \
  --data-urlencode "count=10" \
  --data-urlencode "pos_filter=noun"
```

10. **Нормализация к начальной форме:**
```bash
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=стул" \
  --data-urlencode "count=10" \
  --data-urlencode "pos_filter=noun" \
  --data-urlencode "normalize=true"
```

**Коды ответов:**

- `200 OK` - Успешный запрос
- `400 Bad Request` - Невалидные параметры
- `404 Not Found` - Слово не найдено в словаре
- `500 Internal Server Error` - Внутренняя ошибка сервера

**Примеры ошибок:**

Слово не найдено (404):
```json
{
  "status": "error",
  "error": "word_not_found",
  "message": "Слово 'абвгдейка' не найдено в словаре эмбеддингов"
}
```

Невалидные параметры (400):
```json
{
  "status": "error",
  "error": "invalid_parameters",
  "message": "Параметр 'count' должен быть положительным числом"
}
```

## Расширенные возможности поиска

### Фильтрация по части речи (pos_filter)
Параметр `pos_filter` позволяет получать только слова определенной части речи, используя морфологический анализ pymorphy2.

**Доступные части речи:**

**Основные:**
- `noun` - существительные
- `verb` - глаголы (личные формы)
- `infn` - глаголы (инфинитив)
- `adjf` - прилагательные (полные)
- `adjs` - прилагательные (краткие)
- `advb` - наречия
- `numr` - числительные
- `npro` - местоимения-существительные
- `prtf` - причастия (полные)
- `prts` - причастия (краткие)
- `grnd` - деепричастия

**Удобные группы:**
- `adjective` - все прилагательные (полные + краткие)
- `verb_all` - все глагольные формы (VERB + INFN + причастия + деепричастия)
- `participle` - все причастия (полные + краткие)

**Примеры:**
```bash
# Только существительные
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=дом" \
  --data-urlencode "count=5" \
  --data-urlencode "pos_filter=noun"

# Только прилагательные
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=красный" \
  --data-urlencode "count=5" \
  --data-urlencode "pos_filter=adjective"
```

### Нормализация к начальной форме (normalize)
Параметр `normalize=true` приводит все слова к начальной форме (лемме):
- Существительные → именительный падеж единственного числа
- Прилагательные → мужской род, именительный падеж
- Глаголы → инфинитив

**Примеры:**
- Без нормализации: `["стула", "кресло", "табуретку", "столу", "стол", "стола"]`
- С нормализацией: `["стул", "кресло", "табуретка", "стол"]` (дубликаты автоматически удаляются)

```bash
# Получить существительные в начальной форме
curl -G "http://localhost:8081/api/words" \
  --data-urlencode "word=стул" \
  --data-urlencode "count=10" \
  --data-urlencode "pos_filter=noun" \
  --data-urlencode "normalize=true"
```

**Особенности:**
- Автоматически удаляются дубликаты, возникающие после нормализации (например, "стола" и "столу" → "стол")
- Количество слов в ответе всегда соответствует запрошенному `count`
- Уменьшительно-ласкательные формы (стульчик, столик) сохраняются как отдельные слова

**Использование:** полезно для создания словарей, генерации кроссвордов, или когда нужны слова в канонической форме.

### Stride (шаг выборки)
Параметр `stride` позволяет брать слова с определенным шагом из отсортированного списка по косинусному сходству. Это помогает избежать однокоренных слов и получить более разнообразные результаты.

**Примеры:**
- `stride=0` (по умолчанию): берутся слова последовательно (1-е, 2-е, 3-е...)
- `stride=1`: берутся слова через одно (1-е, 3-е, 5-е...)
- `stride=2`: берутся слова через два (1-е, 4-е, 7-е...)

### Фильтрация похожих слов (similarity_threshold)
Параметр `similarity_threshold` задает порог текстовой схожести слов (доля совпадающих символов). Слова, схожие между собой более чем на указанный порог, будут отфильтрованы.

**Примеры:**
- `similarity_threshold=0.0` (по умолчанию): фильтрация отключена
- `similarity_threshold=0.5`: отфильтровываются слова с 50%+ совпадением символов
- `similarity_threshold=0.7`: отфильтровываются слова с 70%+ совпадением символов

**Рекомендуемые значения:** 0.5-0.7 для избежания однокоренных слов

### Режим случайных слов (random_mode)
При `random_mode=true` возвращаются случайные слова из словаря Navec, игнорируя семантическую близость.

**Использование:** полезно для генерации случайных головоломок или тестирования трансформаций.

## Описание трансформаций

### Перестановка букв (shuffle_letters)
Случайная перестановка букв в словах с учетом настроек фильтрации.

**Пример:**
- Вход: `гроза`
- Выход: `джодь`, `сенг`, `утча`

### Пропуск букв (skip_letters)
Удаление указанного количества случайных букв. При `show_skipped=true` пропущенные буквы заменяются на `_`.

**Примеры:**
- `skip_letters=1, show_skipped=false`: `дждь`, `снг`, `туч`
- `skip_letters=1, show_skipped=true`: `д_ждь`, `сн_г`, `туч_`

### Добавление ошибок (add_errors)
Замена случайных букв на похожие или случайные буквы того же типа (гласные/согласные).

**Пример:**
- Вход: `гроза`
- Выход: `диждь`, `сног`, `тучк`

### Фильтры

#### Тип букв (letter_type)
- `all` - трансформации применяются ко всем буквам
- `vowels` - только к гласным (а, е, ё, и, о, у, ы, э, ю, я)
- `consonants` - только к согласным

#### Сохранение позиций
- `preserve_first=true` - первая буква остается на месте
- `preserve_last=true` - последняя буква остается на месте

## Структура проекта

```
.
├── docker-compose.yml      # Docker Compose конфигурация
├── Dockerfile             # Docker образ
├── requirements.txt       # Python зависимости
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI приложение
│   ├── embeddings.py     # Работа с Navec эмбеддингами
│   ├── transformations.py # Логика трансформаций
│   └── utils.py          # Вспомогательные функции
└── README.md
```

## Разработка

### Локальная разработка без Docker

1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите сервер:
```bash
python -m uvicorn app.main:app --reload --port 8081
```

### Просмотр API документации

После запуска сервиса доступны интерактивные документации:

- Swagger UI: http://localhost:8081/docs
- ReDoc: http://localhost:8081/redoc

## Ограничения

- Работа только с русскоязычными словами
- Словарь ограничен размером модели Navec (~500K слов)
- Трансформации применяются случайным образом (не детерминированы)
- Максимальное значение `count`: 100
- Минимальная длина слова для трансформаций: 3 буквы

## Производительность

- Время ответа: не более 500ms для запросов с `count <= 10`
- Поддержка до 100 одновременных запросов
- Модель загружается один раз при старте приложения

## Логирование

Все запросы и ошибки логируются. Логи доступны через Docker:

```bash
docker-compose logs -f word-morph
```

## Остановка сервиса

```bash
docker-compose down
```

Для удаления volumes (кэша модели):
```bash
docker-compose down -v
```

## Лицензия

MIT