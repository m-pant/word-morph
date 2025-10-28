# Настройка Word Morph MCP в n8n

Это руководство поможет вам подключить Word Morph API как MCP сервер в n8n.

## Предварительные требования

1. Запущенный Word Morph API с MCP сервером:
```bash
docker-compose up -d
```

2. Убедитесь, что контейнеры работают:
```bash
docker ps | grep word-morph
# Должны быть запущены:
# - word-morph-api (порт 8081)
# - word-morph-mcp (порт 8082)
```

3. Проверьте доступность MCP HTTP сервера:
```bash
curl http://localhost:8082/health
# Ответ: {"status":"healthy","service":"word-morph-mcp-http"}
```

## Настройка в n8n

### Шаг 1: Определите endpoint URL

Если n8n запущен на той же машине:
```
http://localhost:8082
```

Если n8n запущен на другой машине в сети:
```
http://<IP_АДРЕС_СЕРВЕРА>:8082
```

Например: `http://192.168.144.105:8082`

### Шаг 2: Настройка MCP Client в n8n

В n8n добавьте узел **"MCP Client"** и настройте следующие параметры:

#### Основные настройки:
- **Protocol Type:** HTTP
- **Base URL (Endpoint):** `http://192.168.144.105:8082` (замените на ваш URL)

**ВАЖНО:** MCP сервер использует JSON-RPC 2.0 протокол на корневом endpoint `/`.

n8n MCP Client будет отправлять запросы в формате:
```json
POST http://192.168.144.105:8082/

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

### Шаг 3: Использование инструмента

После настройки MCP Client вы сможете использовать инструмент `search_similar_words` со следующими параметрами:

#### Обязательные параметры:
- `word` (string) - русское слово для поиска

#### Опциональные параметры:
- `count` (integer, 1-100) - количество слов (по умолчанию 10)
- `pos_filter` (string) - фильтр по части речи: `noun`, `verb`, `adjective`, `adverb`, и др.
- `normalize` (boolean) - привести к начальной форме (именительный падеж)
- `stride` (integer) - шаг выборки для разнообразия результатов
- `similarity_threshold` (float, 0.0-1.0) - порог текстовой схожести
- `random_mode` (boolean) - вернуть случайные слова
- `shuffle_letters` (boolean) - перемешать буквы
- `skip_letters` (integer) - пропустить N букв
- `show_skipped` (boolean) - показать пропущенные буквы как `_`
- `add_errors` (boolean) - добавить случайные ошибки
- `letter_type` (string) - тип букв: `all`, `vowels`, `consonants`
- `preserve_first` (boolean) - сохранить первую букву
- `preserve_last` (boolean) - сохранить последнюю букву

### Примеры использования

#### Пример 1: Простой поиск похожих слов
```json
{
  "tool": "search_similar_words",
  "arguments": {
    "word": "стол",
    "count": 5
  }
}
```

Результат:
```json
{
  "content": [
    {
      "type": "text",
      "text": "✓ Found 5 words for 'стол':\n\nстола, столик, столу, стола, стул"
    }
  ],
  "results": ["стола", "столик", "столу", "стола", "стул"],
  "query": {...}
}
```

#### Пример 2: Поиск существительных с нормализацией
```json
{
  "tool": "search_similar_words",
  "arguments": {
    "word": "дом",
    "count": 5,
    "pos_filter": "noun",
    "normalize": true
  }
}
```

#### Пример 3: Слова с перемешанными буквами
```json
{
  "tool": "search_similar_words",
  "arguments": {
    "word": "гроза",
    "count": 5,
    "shuffle_letters": true,
    "preserve_first": true
  }
}
```

#### Пример 4: Прилагательные с фильтрацией похожих
```json
{
  "tool": "search_similar_words",
  "arguments": {
    "word": "красный",
    "count": 10,
    "pos_filter": "adjective",
    "similarity_threshold": 0.6
  }
}
```

## Альтернатива: Прямой HTTP запрос (без MCP Client)

Если вы хотите использовать простой HTTP Request узел в n8n вместо MCP Client:

### Endpoint: POST /search

```
URL: http://192.168.144.105:8082/search
Method: POST
Content-Type: application/json

Body:
{
  "word": "дом",
  "count": 5,
  "pos_filter": "noun",
  "normalize": true
}
```

Этот endpoint возвращает прямой ответ от Word Morph API без обертки MCP protocol.

## Проверка работоспособности

### Через curl:

```bash
# Проверка health
curl http://192.168.144.105:8082/health

# Список инструментов (JSON-RPC 2.0)
curl -X POST http://192.168.144.105:8082/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'

# Вызов инструмента (JSON-RPC 2.0)
curl -X POST http://192.168.144.105:8082/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search_similar_words",
      "arguments": {
        "word": "стол",
        "count": 3
      }
    }
  }'

# Альтернативные REST endpoints (для прямых HTTP запросов):
curl http://192.168.144.105:8082/tools
curl -X POST http://192.168.144.105:8082/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "search_similar_words", "arguments": {"word": "стол", "count": 3}}'

# Прямой поиск
curl -X POST http://192.168.144.105:8082/search \
  -H "Content-Type: application/json" \
  -d '{
    "word": "дом",
    "count": 5,
    "pos_filter": "noun"
  }'
```

### Интерактивная документация:

Откройте в браузере:
```
http://192.168.144.105:8082/docs
```

Здесь вы можете протестировать все endpoints через Swagger UI.

## Устранение неполадок

### Ошибка: Connection refused

**Причина:** MCP сервер не запущен или недоступен.

**Решение:**
```bash
# Проверьте статус контейнеров
docker ps | grep word-morph

# Перезапустите сервисы
docker-compose restart

# Проверьте логи
docker-compose logs -f mcp-server
```

### Ошибка: 503 Connection Error

**Причина:** MCP сервер не может подключиться к основному API.

**Решение:**
```bash
# Проверьте, что API работает
curl http://localhost:8081/health

# Проверьте логи MCP сервера
docker logs word-morph-mcp
```

### Ошибка: 400 Bad Request

**Причина:** Неверные параметры запроса.

**Решение:** Убедитесь, что:
- Параметр `word` содержит русское слово в кириллице
- `count` находится в диапазоне 1-100
- `pos_filter` содержит валидное значение
- `similarity_threshold` находится в диапазоне 0.0-1.0

## Полезные ссылки

- Основная документация API: см. README.md
- Swagger UI: http://192.168.144.105:8082/docs
- Health check: http://192.168.144.105:8082/health
- Список инструментов: http://192.168.144.105:8082/tools
