# ai-agent-toolbox

Локальный AI-agent toolbox на Python 3.11+ с LangChain, OpenAI-compatible LLM, CLI и **русскоязычным** web-интерфейсом Streamlit.

## Чем AI-agent отличается от обычной LLM

Обычная LLM отвечает только на основе своих знаний и текущего промпта. **AI-agent** дополнительно:

- **выбирает инструменты** по смыслу запроса (погода, файлы, калькулятор и т.д.);
- **вызывает внешние API и локальные функции** и возвращает реальные данные;
- **ведёт память диалога** между запросами;
- **логирует действия** для отладки и прозрачности.

То есть agent = LLM + tools + memory + orchestration.

## 11 инструментов

1. **web_search** — Поиск в интернете (DuckDuckGo)
2. **get_weather** — Погода по городу (Open-Meteo)
3. **get_crypto_price** — Курс криптовалют (CoinGecko)
4. **file_manager** — Работа с файлами в `data/files`
5. **memory_manager** — Память агента (`memory.json`)
6. **get_fx_rate** — Курсы обычных валют (Frankfurter / fallback)
7. **generate_qr_code** — Генерация QR-кодов в `data/qr_codes`
8. **reminder_manager** — Локальные напоминания (`data/reminders.json`)
9. **calculator** — Безопасный калькулятор (без `eval`)
10. **unit_converter** — Конвертер единиц (км/мили, кг/фунты, °C/°F и др.)
11. **text_stats** — Статистика текста или файла

Единый каталог описаний — в `agent/tool_catalog.py` (`TOOL_CATALOG`).

## Быстрый старт

### 1. Установка

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # Windows
```

### 2. Переменные окружения

В файле `.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

### 3. CLI

```bash
python run.py
```

В консоли показывается только чистый диалог (`Вы:` / `Агент:`). Технические INFO-логи пишутся в `agent.log`.

Команды CLI:

- `exit` / `quit` — выход
- `/memory` — показать summary из `memory.json`
- `/clear-memory` — очистить память

### 4. Web (Streamlit, русский интерфейс)

```bash
streamlit run app/streamlit_app.py
```

Web-интерфейс показывает созданные артефакты прямо в чате:

- QR-коды — компактный preview (~280 px в чате, ~180 px в sidebar) и кнопка «Скачать …png»;
- созданные TXT/MD/JSON доступны для скачивания и предпросмотра в expander;
- статистика файла считается через `text_stats` с `action="analyze_file"` и именем файла;
- sidebar содержит списки файлов и QR с download-кнопками;
- память и технические логи вынесены в sidebar и не смешиваются с чатом.

## Тестовые запросы

- «Что ты умеешь?»
- «Найди краткую информацию о LangChain agents»
- «Какая сейчас погода в Helsinki?»
- «Сколько стоит bitcoin в usd?»
- «Какой курс EUR к USD?»
- «Создай файл agent_notes.txt с 5 отличиями AI-агента от обычной LLM»
- «Создай QR-код для https://github.com/eliv1982 как github_qr.png»
- «Посчитай (12500 * 0.2) + 390»
- «Переведи 15 километров в мили»

## Тесты

```bash
python -m pytest -q
python -m compileall . -q
```

Тесты покрывают deterministic tools и каталог инструментов; `OPENAI_API_KEY` не требуется.

Перед сдачей убедитесь, что **pytest** и **compileall** проходят без ошибок.

## Структура проекта

```
ai-agent-toolbox-homework/
├── agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── tools.py
│   ├── tool_catalog.py
│   ├── memory.py
│   └── logging_config.py
├── app/
│   ├── streamlit_app.py
│   └── ui_helpers.py
├── data/
│   ├── files/
│   │   └── .gitkeep
│   ├── qr_codes/
│   │   └── .gitkeep
│   └── reminders.json      # runtime, создаётся автоматически, не коммитится
├── tests/
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

**Runtime-файлы** (создаются при работе агента, в git не попадают):

- `memory.json` — история диалога
- `agent.log` — технические логи
- `data/reminders.json` — локальные напоминания
- `data/files/*` и `data/qr_codes/*` — пользовательские файлы и QR (кроме `.gitkeep`)

## Безопасность

- Файлы только в `data/files` (защита от path traversal)
- QR-коды только в `data/qr_codes`
- Нет произвольных terminal commands
- `.env`, `agent.log`, `memory.json` и пользовательские файлы не коммитятся

## Что улучшено сверх урока

- **Streamlit UI на русском** — заголовки, sidebar, demo-кнопки, плейсхолдер чата
- **11 инструментов** с единым каталогом `TOOL_CATALOG` для prompt и UI
- **Чистый CLI** — диалог отделён от INFO-логов (логи только в `agent.log`)
- **Разделение чата и техники** — memory, files, QR, logs в sidebar/expander, не в чате
- **Sandbox** для файлов и QR preview
- **Автосохранение** истории в `memory.json`
- **Unit-тесты** для deterministic tools и каталога инструментов

## Что показать на скриншотах

1. **Главная web-страница** — заголовок, чат и sidebar со списком **11 инструментов**
2. **Capabilities** — ответ на «Что ты умеешь?» (11 отдельных пунктов)
3. **Web search** — поиск через DuckDuckGo
4. **Weather / Crypto / FX** — погода, криптовалюта и курс валют
5. **Создание файла** — артефакт в чате: preview + download TXT
6. **Статистика текста из файла** — `text_stats` по `demo_summary.txt` (ненулевые значения)
7. **QR preview + download** — компактный QR в чате и кнопка «Скачать …png»
8. **Calculator / unit converter / reminder** — примеры вычислений, конвертации и напоминания
9. **Sidebar** — блоки памяти, файлов, QR-кодов и expander с техническими логами
10. **pytest + compileall** — успешный вывод `python -m pytest -q` и `python -m compileall . -q`

## Лицензия


