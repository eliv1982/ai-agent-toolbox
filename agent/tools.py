"""Agent tools: plain Python functions with LangChain @tool wrappers."""

from __future__ import annotations

import ast
import json
import logging
import operator
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import qrcode
import requests
from langchain_core.tools import tool

from agent.logging_config import setup_logging
from agent.memory import add_memory_entry, clear_memory, load_memory

setup_logging()
logger = logging.getLogger("agent.tools")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FILES_DIR = PROJECT_ROOT / "data" / "files"
QR_CODES_DIR = PROJECT_ROOT / "data" / "qr_codes"
REMINDERS_FILE = PROJECT_ROOT / "data" / "reminders.json"
MEMORY_FILE = PROJECT_ROOT / "memory.json"

REQUEST_TIMEOUT = 15

WEATHER_CODES = {
    0: "Ясно",
    1: "Преимущественно ясно",
    2: "Переменная облачность",
    3: "Пасмурно",
    45: "Туман",
    48: "Изморозь",
    51: "Моросящий дождь",
    53: "Моросящий дождь",
    55: "Сильный моросящий дождь",
    61: "Небольшой дождь",
    63: "Дождь",
    65: "Сильный дождь",
    71: "Небольшой снег",
    73: "Снег",
    75: "Сильный снег",
    80: "Ливень",
    95: "Гроза",
}


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^\w.\-]", "_", name, flags=re.UNICODE)
    if not name.lower().endswith(".png"):
        name = f"{name}.png"
    return name or "qr_code.png"


def _resolve_files_path(relative_path: str) -> Path:
    base = FILES_DIR.resolve()
    target = (FILES_DIR / relative_path).resolve()
    if base not in target.parents and target != base:
        raise ValueError("Path traversal detected: access outside data/files is forbidden")
    return target


def _load_reminders() -> list[dict[str, Any]]:
    if not REMINDERS_FILE.exists():
        return []
    try:
        with REMINDERS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_reminders(items: list[dict[str, Any]]) -> None:
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REMINDERS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 1. web_search
# ---------------------------------------------------------------------------


def web_search_impl(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web via DuckDuckGo."""
    logger.info("web_search called: query=%r", query)
    try:
        from ddgs import DDGS

        with DDGS(timeout=REQUEST_TIMEOUT) as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        formatted = [
            {
                "title": item.get("title", ""),
                "url": item.get("href", item.get("url", "")),
                "snippet": item.get("body", item.get("snippet", "")),
            }
            for item in results
        ]
        logger.info("web_search success: %d results", len(formatted))
        return formatted
    except ImportError:
        try:
            from duckduckgo_search import DDGS as LegacyDDGS

            with LegacyDDGS(timeout=REQUEST_TIMEOUT) as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            formatted = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("href", item.get("url", "")),
                    "snippet": item.get("body", item.get("snippet", "")),
                }
                for item in results
            ]
            logger.info("web_search success (legacy): %d results", len(formatted))
            return formatted
        except Exception as exc:
            logger.exception("web_search import/search error")
            return [{"error": f"Search failed: {exc}"}]
    except Exception as exc:
        logger.exception("web_search error")
        return [{"error": f"Search failed: {exc}"}]


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Returns title, url and snippet for each result."""
    results = web_search_impl(query)
    if not results:
        return "Результаты не найдены."
    lines = []
    for idx, item in enumerate(results, start=1):
        if "error" in item:
            return item["error"]
        lines.append(
            f"{idx}. {item['title']}\n   URL: {item['url']}\n   {item['snippet']}"
        )
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# 2. get_weather
# ---------------------------------------------------------------------------


def get_weather_impl(city: str) -> dict[str, Any]:
    """Get current weather for a city via Open-Meteo."""
    logger.info("get_weather called: city=%r", city)
    try:
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "ru", "format": "json"},
            timeout=REQUEST_TIMEOUT,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        results = geo_data.get("results") or []
        if not results:
            return {"error": f"Город '{city}' не найден"}

        place = results[0]
        latitude = place["latitude"]
        longitude = place["longitude"]
        resolved_city = place.get("name", city)
        country = place.get("country", "")

        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code",
                "timezone": "auto",
            },
            timeout=REQUEST_TIMEOUT,
        )
        weather_resp.raise_for_status()
        current = weather_resp.json().get("current", {})
        code = int(current.get("weather_code", -1))
        result = {
            "city": resolved_city,
            "country": country,
            "temperature_c": current.get("temperature_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_direction_deg": current.get("wind_direction_10m"),
            "weather_code": code,
            "description": WEATHER_CODES.get(code, "Неизвестные условия"),
        }
        logger.info("get_weather success: %s", result)
        return result
    except requests.Timeout:
        logger.error("get_weather timeout")
        return {"error": "Timeout while fetching weather data"}
    except requests.RequestException as exc:
        logger.exception("get_weather request error")
        return {"error": f"Weather API error: {exc}"}


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city. Uses Open-Meteo geocoding and forecast APIs."""
    data = get_weather_impl(city)
    if "error" in data:
        return data["error"]
    return (
        f"Город: {data['city']}, {data['country']}\n"
        f"Температура: {data['temperature_c']} °C\n"
        f"Ветер: {data['wind_speed_kmh']} км/ч, направление {data['wind_direction_deg']}°\n"
        f"Код погоды: {data['weather_code']}\n"
        f"Описание: {data['description']}"
    )


# ---------------------------------------------------------------------------
# 3. get_crypto_price
# ---------------------------------------------------------------------------


def get_crypto_price_impl(coin: str, currency: str = "usd") -> dict[str, Any]:
    """Get cryptocurrency price from CoinGecko."""
    logger.info("get_crypto_price called: coin=%r currency=%r", coin, currency)
    coin_id = coin.lower().strip()
    curr = currency.lower().strip()
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": curr},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        if coin_id not in payload or curr not in payload[coin_id]:
            return {"error": f"Coin '{coin}' or currency '{currency}' not found"}
        result = {
            "coin": coin_id,
            "currency": curr,
            "price": payload[coin_id][curr],
            "source": "CoinGecko",
        }
        logger.info("get_crypto_price success: %s", result)
        return result
    except requests.RequestException as exc:
        logger.exception("get_crypto_price error")
        return {"error": f"Crypto API error: {exc}"}


@tool
def get_crypto_price(coin: str, currency: str = "usd") -> str:
    """Get cryptocurrency price. Examples: coin=bitcoin, currency=usd."""
    data = get_crypto_price_impl(coin, currency)
    if "error" in data:
        return data["error"]
    return (
        f"Coin: {data['coin']}\n"
        f"Currency: {data['currency'].upper()}\n"
        f"Price: {data['price']}\n"
        f"Source: {data['source']}"
    )


# ---------------------------------------------------------------------------
# 4. file_manager
# ---------------------------------------------------------------------------


def file_manager_impl(action: str, filename: str = "", content: str = "") -> dict[str, Any]:
    """Safely manage files inside data/files."""
    logger.info("file_manager called: action=%r filename=%r", action, filename)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    action = action.lower().strip()

    try:
        if action == "list":
            files = sorted(
                p.name for p in FILES_DIR.iterdir() if p.is_file() and p.name != ".gitkeep"
            )
            return {"action": "list", "files": files}

        if not filename:
            return {"error": "filename is required for this action"}

        path = _resolve_files_path(filename)

        if action == "read":
            if not path.exists():
                return {"error": f"File not found: {filename}"}
            text = path.read_text(encoding="utf-8")
            return {"action": "read", "filename": filename, "content": text}

        if action == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"action": "write", "filename": filename, "status": "ok"}

        if action == "append":
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(content)
            return {"action": "append", "filename": filename, "status": "ok"}

        return {"error": f"Unsupported action: {action}"}
    except ValueError as exc:
        logger.warning("file_manager security block: %s", exc)
        return {"error": str(exc)}
    except OSError as exc:
        logger.exception("file_manager IO error")
        return {"error": f"File operation failed: {exc}"}


@tool
def file_manager(action: str, filename: str = "", content: str = "") -> str:
    """Manage files in data/files. Actions: list, read, write, append."""
    data = file_manager_impl(action, filename, content)
    if "error" in data:
        return data["error"]
    if data["action"] == "list":
        files = data.get("files", [])
        return "Files:\n" + ("\n".join(files) if files else "(empty)")
    if data["action"] == "read":
        return f"Content of {data['filename']}:\n{data['content']}"
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 5. memory_manager
# ---------------------------------------------------------------------------


def memory_manager_impl(action: str, note: str = "") -> dict[str, Any]:
    """Manage persistent memory in memory.json."""
    logger.info("memory_manager called: action=%r", action)
    action = action.lower().strip()

    if action == "add":
        entry = add_memory_entry(note=note or "Manual note")
        return {"action": "add", "entry": entry}

    if action == "list":
        entries = load_memory()
        return {"action": "list", "entries": entries}

    if action == "clear":
        clear_memory()
        return {"action": "clear", "status": "memory cleared"}

    return {"error": f"Unsupported action: {action}"}


@tool
def memory_manager(action: str, note: str = "") -> str:
    """Manage conversation memory. Actions: add, list, clear."""
    data = memory_manager_impl(action, note)
    if "error" in data:
        return data["error"]
    if data["action"] == "list":
        entries = data.get("entries", [])
        if not entries:
            return "Memory is empty."
        lines = []
        for item in entries[-10:]:
            lines.append(
                f"[{item.get('timestamp', '')}] "
                f"user={item.get('user_message', '')} | "
                f"assistant={item.get('assistant_response', '')} | "
                f"note={item.get('note', '')}"
            )
        return "\n".join(lines)
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 6. get_fx_rate
# ---------------------------------------------------------------------------


def get_fx_rate_impl(base: str, target: str) -> dict[str, Any]:
    """Get FX rate from Frankfurter with exchangerate.host fallback."""
    logger.info("get_fx_rate called: base=%r target=%r", base, target)
    base_code = base.upper().strip()
    target_code = target.upper().strip()

    try:
        resp = requests.get(
            f"https://api.frankfurter.app/latest",
            params={"from": base_code, "to": target_code},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 404:
            return {"error": f"Currency not supported: {base_code} or {target_code}"}
        resp.raise_for_status()
        payload = resp.json()
        rate = payload.get("rates", {}).get(target_code)
        if rate is None:
            return {"error": f"Currency not supported: {target_code}"}
        return {
            "base": base_code,
            "target": target_code,
            "rate": rate,
            "date": payload.get("date"),
            "source": "Frankfurter",
        }
    except requests.RequestException as frank_exc:
        logger.warning("Frankfurter failed, trying fallback: %s", frank_exc)
        try:
            resp = requests.get(
                "https://api.exchangerate.host/convert",
                params={"from": base_code, "to": target_code},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("success", True) and payload.get("result") is None:
                return {"error": f"Currency not supported: {base_code} or {target_code}"}
            return {
                "base": base_code,
                "target": target_code,
                "rate": payload.get("result"),
                "date": payload.get("date") or datetime.now(timezone.utc).date().isoformat(),
                "source": "exchangerate.host",
            }
        except requests.RequestException as exc:
            logger.exception("get_fx_rate error")
            return {"error": f"FX API error: {exc}"}


@tool
def get_fx_rate(base: str, target: str) -> str:
    """Get exchange rate between fiat currencies, e.g. base=EUR target=USD."""
    data = get_fx_rate_impl(base, target)
    if "error" in data:
        return data["error"]
    return (
        f"Base: {data['base']}\n"
        f"Target: {data['target']}\n"
        f"Rate: {data['rate']}\n"
        f"Date: {data['date']}\n"
        f"Source: {data['source']}"
    )


# ---------------------------------------------------------------------------
# 7. generate_qr_code
# ---------------------------------------------------------------------------


def generate_qr_code_impl(text: str, filename: str = "qr_code.png") -> dict[str, Any]:
    """Generate QR code PNG in data/qr_codes."""
    logger.info("generate_qr_code called: filename=%r", filename)
    QR_CODES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(filename)
    output_path = QR_CODES_DIR / safe_name

    try:
        img = qrcode.make(text)
        img.save(output_path)
        result = {"text": text, "path": str(output_path.relative_to(PROJECT_ROOT))}
        logger.info("generate_qr_code success: %s", result)
        return result
    except Exception as exc:
        logger.exception("generate_qr_code error")
        return {"error": f"QR generation failed: {exc}"}


@tool
def generate_qr_code(text: str, filename: str = "qr_code.png") -> str:
    """Generate a QR code PNG for text or URL and save it to data/qr_codes."""
    data = generate_qr_code_impl(text, filename)
    if "error" in data:
        return data["error"]
    return f"QR code saved to: {data['path']}"


# ---------------------------------------------------------------------------
# 8. reminder_manager
# ---------------------------------------------------------------------------


def reminder_manager_impl(action: str, reminder_text: str = "", due_text: str = "") -> dict[str, Any]:
    """Manage local reminders stored in data/reminders.json."""
    logger.info("reminder_manager called: action=%r", action)
    action = action.lower().strip()

    if action == "add":
        items = _load_reminders()
        entry = {
            "timestamp_created": datetime.now(timezone.utc).isoformat(),
            "reminder_text": reminder_text,
            "due_text": due_text,
        }
        items.append(entry)
        _save_reminders(items)
        return {"action": "add", "entry": entry}

    if action == "list":
        return {"action": "list", "reminders": _load_reminders()}

    if action == "clear":
        _save_reminders([])
        return {"action": "clear", "status": "reminders cleared"}

    return {"error": f"Unsupported action: {action}"}


@tool
def reminder_manager(action: str, reminder_text: str = "", due_text: str = "") -> str:
    """Manage reminders without background scheduler. Actions: add, list, clear."""
    data = reminder_manager_impl(action, reminder_text, due_text)
    if "error" in data:
        return data["error"]
    if data["action"] == "list":
        reminders = data.get("reminders", [])
        if not reminders:
            return "No reminders yet."
        lines = []
        for item in reminders:
            lines.append(
                f"- [{item.get('timestamp_created', '')}] "
                f"{item.get('reminder_text', '')} (due: {item.get('due_text', '')})"
            )
        return "\n".join(lines)
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 9. calculator
# ---------------------------------------------------------------------------

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_ast_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_ast_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _eval_ast_node(node.left)
        right = _eval_ast_node(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ValueError("Division by zero")
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent too large")
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    raise ValueError("Unsupported expression")


def calculator_impl(expression: str) -> dict[str, Any]:
    """Safely evaluate arithmetic expressions."""
    logger.info("calculator called: expression=%r", expression)
    cleaned = expression.strip()
    if not cleaned:
        return {"error": "Empty expression"}
    try:
        tree = ast.parse(cleaned, mode="eval")
        result = _eval_ast_node(tree)
        if result == int(result):
            result = int(result)
        payload = {"expression": cleaned, "result": result}
        logger.info("calculator success: %s", payload)
        return payload
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as exc:
        logger.warning("calculator error: %s", exc)
        return {"error": f"Invalid expression: {exc}"}


@tool
def calculator(expression: str) -> str:
    """Safely evaluate math expressions with +, -, *, /, ** and parentheses."""
    data = calculator_impl(expression)
    if "error" in data:
        return data["error"]
    return f"{data['expression']} = {data['result']}"


# ---------------------------------------------------------------------------
# 10. unit_converter
# ---------------------------------------------------------------------------

_CONVERSIONS = {
    "km_to_miles": lambda v: v * 0.621371,
    "miles_to_km": lambda v: v / 0.621371,
    "kg_to_lb": lambda v: v * 2.20462,
    "lb_to_kg": lambda v: v / 2.20462,
    "c_to_f": lambda v: v * 9 / 5 + 32,
    "f_to_c": lambda v: (v - 32) * 5 / 9,
    "cm_to_inches": lambda v: v / 2.54,
    "inches_to_cm": lambda v: v * 2.54,
}


def unit_converter_impl(value: float, conversion_type: str) -> dict[str, Any]:
    """Convert units using predefined conversion types."""
    logger.info("unit_converter called: value=%r type=%r", value, conversion_type)
    key = conversion_type.lower().strip()
    if key not in _CONVERSIONS:
        supported = ", ".join(sorted(_CONVERSIONS))
        return {"error": f"Unsupported conversion_type. Supported: {supported}"}
    result = _CONVERSIONS[key](float(value))
    payload = {
        "value": value,
        "conversion_type": key,
        "result": round(result, 6),
    }
    logger.info("unit_converter success: %s", payload)
    return payload


@tool
def unit_converter(value: float, conversion_type: str) -> str:
    """Convert units. Types: km_to_miles, miles_to_km, kg_to_lb, lb_to_kg, c_to_f, f_to_c, cm_to_inches, inches_to_cm."""
    data = unit_converter_impl(value, conversion_type)
    if "error" in data:
        return data["error"]
    return f"{data['value']} ({data['conversion_type']}) = {data['result']}"


# ---------------------------------------------------------------------------
# 11. text_stats
# ---------------------------------------------------------------------------


def text_stats_impl(action: str, text: str = "", filename: str = "") -> dict[str, Any]:
    """Analyze text or a file inside data/files."""
    logger.info(
        "text_stats called: action=%r text_len=%s filename=%r",
        action,
        len(text) if text else 0,
        filename,
    )
    action = action.lower().strip()

    if action == "analyze_text":
        if text is None or not str(text).strip():
            return {
                "error": (
                    "Для анализа текста передайте непустой text или используйте "
                    "action='analyze_file' с filename."
                )
            }
        content = str(text)
    elif action == "analyze_file":
        if not filename or not str(filename).strip():
            return {"error": "filename is required for analyze_file"}
        safe_name = Path(str(filename).strip()).name
        try:
            path = _resolve_files_path(safe_name)
            if not path.exists():
                return {"error": f"File not found: {safe_name}"}
            content = path.read_text(encoding="utf-8")
            if not content.strip():
                return {"error": f"Файл пуст: {safe_name}"}
        except ValueError as exc:
            return {"error": str(exc)}
        except OSError as exc:
            return {"error": f"Cannot read file: {exc}"}
    else:
        return {"error": f"Unsupported action: {action}"}

    char_count = len(content)
    words = re.findall(r"\b\w+\b", content, flags=re.UNICODE)
    word_count = len(words)
    line_count = content.count("\n") + (1 if content else 0)
    reading_minutes = round(max(word_count, 1) / 200, 2)

    result = {
        "action": action,
        "filename": safe_name if action == "analyze_file" else "",
        "characters": char_count,
        "words": word_count,
        "lines": line_count,
        "reading_time_minutes": reading_minutes,
    }
    logger.info("text_stats success: %s", result)
    return result


@tool
def text_stats(action: str, text: str = "", filename: str = "") -> str:
    """Статистика текста или файла из data/files.

    Используй action='analyze_file' и filename (например demo_summary.txt),
    когда нужна статистика существующего файла.
    Используй action='analyze_text' и непустой text только для прямого анализа строки.
    Не вызывай analyze_text с пустым text после чтения файла другим инструментом.
    """
    data = text_stats_impl(action, text, filename)
    if "error" in data:
        return data["error"]
    label = data.get("filename") or "text"
    return (
        f"Источник: {label}\n"
        f"Символов: {data['characters']}\n"
        f"Слов: {data['words']}\n"
        f"Строк: {data['lines']}\n"
        f"Время чтения (мин): {data['reading_time_minutes']}"
    )


ALL_TOOLS = [
    web_search,
    get_weather,
    get_crypto_price,
    file_manager,
    memory_manager,
    get_fx_rate,
    generate_qr_code,
    reminder_manager,
    calculator,
    unit_converter,
    text_stats,
]
