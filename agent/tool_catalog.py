"""Unified catalog of agent tools for prompts and UI."""

from __future__ import annotations

import re
from typing import TypedDict

REQUIRED_FIELDS = ("name", "title_ru", "description_ru", "example_prompt_ru", "capability_line_ru")


class ToolCatalogItem(TypedDict):
    name: str
    title_ru: str
    description_ru: str
    example_prompt_ru: str
    capability_line_ru: str


TOOL_CATALOG: list[ToolCatalogItem] = [
    {
        "name": "web_search",
        "title_ru": "Поиск в интернете",
        "description_ru": "Ищет актуальную информацию через DuckDuckGo и возвращает заголовки, ссылки и сниппеты.",
        "example_prompt_ru": "Найди краткую информацию о LangChain agents",
        "capability_line_ru": "Искать информацию в интернете.",
    },
    {
        "name": "get_weather",
        "title_ru": "Погода по городу",
        "description_ru": "Получает текущую погоду для указанного города через Open-Meteo.",
        "example_prompt_ru": "Какая сейчас погода в Helsinki?",
        "capability_line_ru": "Получать текущую погоду по названию города.",
    },
    {
        "name": "get_crypto_price",
        "title_ru": "Курс криптовалют",
        "description_ru": "Возвращает текущую цену криптовалюты через CoinGecko.",
        "example_prompt_ru": "Сколько стоит bitcoin в usd?",
        "capability_line_ru": "Проверять курс криптовалют, например bitcoin, ethereum или litecoin.",
    },
    {
        "name": "file_manager",
        "title_ru": "Работа с файлами",
        "description_ru": "Безопасно читает, записывает и перечисляет файлы внутри data/files.",
        "example_prompt_ru": "Создай файл agent_notes.txt с 5 отличиями AI-агента от обычной LLM",
        "capability_line_ru": "Читать, создавать и дополнять файлы в рабочей папке.",
    },
    {
        "name": "memory_manager",
        "title_ru": "Память агента",
        "description_ru": "Добавляет, просматривает и очищает записи в memory.json.",
        "example_prompt_ru": "Покажи последние записи памяти",
        "capability_line_ru": "Сохранять и показывать локальную память агента.",
    },
    {
        "name": "get_fx_rate",
        "title_ru": "Курсы обычных валют",
        "description_ru": "Возвращает курс обмена между обычными валютами через Frankfurter API.",
        "example_prompt_ru": "Какой курс EUR к USD?",
        "capability_line_ru": "Получать курсы обычных валют, например EUR к USD или USD к RUB.",
    },
    {
        "name": "generate_qr_code",
        "title_ru": "Генерация QR-кодов",
        "description_ru": "Создаёт PNG QR-код для текста или URL и сохраняет в data/qr_codes.",
        "example_prompt_ru": "Создай QR-код для https://github.com/eliv1982 как github_qr.png",
        "capability_line_ru": "Генерировать QR-коды и сохранять их как PNG.",
    },
    {
        "name": "reminder_manager",
        "title_ru": "Локальные напоминания",
        "description_ru": "Добавляет, показывает и очищает напоминания в data/reminders.json.",
        "example_prompt_ru": "Добавь напоминание: проверить результаты ДЗ завтра в 10:00",
        "capability_line_ru": "Сохранять локальные напоминания.",
    },
    {
        "name": "calculator",
        "title_ru": "Калькулятор",
        "description_ru": "Безопасно вычисляет арифметические выражения с +, -, *, /, ** и скобками.",
        "example_prompt_ru": "Посчитай (12500 * 0.2) + 390",
        "capability_line_ru": "Выполнять безопасные математические вычисления.",
    },
    {
        "name": "unit_converter",
        "title_ru": "Конвертер единиц измерения",
        "description_ru": "Конвертирует км/мили, кг/фунты, °C/°F, см/дюймы.",
        "example_prompt_ru": "Переведи 15 километров в мили",
        "capability_line_ru": (
            "Конвертировать единицы измерения: километры, мили, килограммы, "
            "фунты, градусы, сантиметры и дюймы."
        ),
    },
    {
        "name": "text_stats",
        "title_ru": "Статистика текста",
        "description_ru": "Считает символы, слова, строки и время чтения для текста или файла.",
        "example_prompt_ru": "Посчитай статистику текста: AI-агент — это LLM плюс инструменты и память.",
        "capability_line_ru": (
            "Считать статистику текста: слова, символы, строки и примерное время чтения."
        ),
    },
]

DEMO_PROMPTS_RU: list[str] = [
    "Что ты умеешь?",
    "Найди краткую информацию о LangChain agents",
    "Какая сейчас погода в Helsinki?",
    "Сколько стоит bitcoin in usd?",
    "Какой курс EUR к USD?",
    "Создай файл agent_notes.txt с 5 отличиями AI-агента от обычной LLM",
    "Прочитай agent_notes.txt и сделай краткое резюме",
    "Создай QR-код для https://github.com/eliv1982 как github_qr.png",
    "Добавь напоминание: проверить результаты ДЗ завтра в 10:00",
    "Посчитай (12500 * 0.2) + 390",
    "Переведи 15 километров в мили",
    "Посчитай статистику текста: AI-агент — это LLM плюс инструменты и память.",
]

_CAPABILITIES_PATTERNS = (
    r"что\s+ты\s+умеешь",
    r"что\s+умеешь",
    r"какие\s+у\s+тебя\s+инструменты",
    r"какие\s+инструменты",
    r"\bhelp\b",
    r"помощь",
)


def is_capabilities_query(user_input: str) -> bool:
    """Return True if the user asks about agent capabilities."""
    normalized = user_input.lower().strip()
    return any(re.search(pattern, normalized) for pattern in _CAPABILITIES_PATTERNS)


def format_tool_catalog_for_prompt() -> str:
    """Format all 11 tools as numbered list for the system prompt."""
    lines: list[str] = []
    for index, tool in enumerate(TOOL_CATALOG, start=1):
        lines.append(
            f"{index}. {tool['name']} — {tool['title_ru']}: {tool['description_ru']}"
        )
    return "\n".join(lines)


def format_capabilities_ru() -> str:
    """Return deterministic Russian capabilities text for help/capabilities queries."""
    lines = ["Я локальный AI-агент с 11 инструментами. Могу:", ""]
    for index, tool in enumerate(TOOL_CATALOG, start=1):
        lines.append(f"{index}. {tool['capability_line_ru']}")
    return "\n".join(lines)
