"""CLI entry point for the local AI agent toolbox."""

from __future__ import annotations

import sys

from colorama import Fore, Style, init

from agent.agent import ask_agent
from agent.logging_config import setup_logging
from agent.memory import clear_memory, summarize_memory_for_prompt

init(autoreset=True)
logger = setup_logging()


def print_banner() -> None:
    print(Fore.CYAN + Style.BRIGHT + "🧰 Локальный AI-агент Toolbox (CLI)")
    print(Style.RESET_ALL + "Команды: exit/quit, /memory, /clear-memory")
    print("-" * 50)


def main() -> None:
    print_banner()
    while True:
        try:
            user_input = input(Fore.GREEN + "Вы: " + Style.RESET_ALL).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in {"exit", "quit"}:
            print("До свидания!")
            break

        if lowered == "/memory":
            print(Fore.YELLOW + summarize_memory_for_prompt(limit=20) + Style.RESET_ALL)
            continue

        if lowered == "/clear-memory":
            clear_memory()
            print(Fore.YELLOW + "Память очищена." + Style.RESET_ALL)
            continue

        try:
            response = ask_agent(user_input)
            print(Fore.BLUE + "Агент: " + Style.RESET_ALL + response)
        except RuntimeError as exc:
            print(Fore.RED + str(exc) + Style.RESET_ALL, file=sys.stderr)
            break
        except Exception as exc:
            logger.exception("CLI error")
            print(Fore.RED + f"Ошибка: {exc}" + Style.RESET_ALL, file=sys.stderr)


if __name__ == "__main__":
    main()
