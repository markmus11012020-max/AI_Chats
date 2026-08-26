"""Chains: цепочка для генерации Python-кода по текстовому заданию.

Шаги:
  1) analysis_chain — анализ задания -> структура.
  2) tools_chain    — подбор инструментов / библиотек.
  3) code_chain     — генерация полного Python-кода.
  4) review_chain   — минимальная проверка через LLM + локальный ast.parse.

CLI: python script.py "Анализ данных по ставке ЦБ"
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from langchain_openai import ChatOpenAI


ANALYSIS_SYSTEM = (
    "Ты — senior-аналитик. Проанализируй техническое задание пользователя и верни "
    "СТРОГО валидный JSON без markdown-обёрток (без ```json```) со следующей структурой:\n\n"
    "{\n"
    '  "task_summary": "краткое описание задачи 1-2 предложения",\n'
    '  "commands": ["список ключевых команд/действий"],\n'
    '  "handlers": ["список обработчиков / функций"],\n'
    '  "output_format": "описание формата вывода",\n'
    '  "needs_database": true/false,\n'
    '  "database_hint": "какая БД нужна",\n'
    '  "extra_dependencies": ["список дополнительных pip-пакетов"],\n'
    '  "language": "python",\n'
    '  "complexity": "simple | medium | complex"\n'
    "}\n\n"
    "Верни ТОЛЬКО JSON, без markdown-обёрток."
)

TOOLS_SYSTEM = (
    "Ты — python-разработчик. Подбери инструменты для генерации кода. "
    "Верни СТРОГО валидный JSON без markdown-обёрток:\n\n"
    "{\n"
    '  "standard_libs": ["stdlib модули"],\n'
    '  "external_libs": ["внешние pip-пакеты"],\n'
    '  "patterns": ["паттерны проектирования"],\n'
    '  "entry_point": "название главной функции",\n'
    '  "cli_style": "argparse | function | class",\n'
    '  "notes": "короткий комментарий"\n'
    "}\n\n"
    "Верни ТОЛЬКО JSON, без markdown-обёрток."
)

CODE_SYSTEM = (
    "Ты — Python-разработчик. Сгенерируй полный рабочий Python-скрипт. "
    "Требования: Python 3.10+, docstring, импорты сверху, argparse, "
    'if __name__ == "__main__": в конце, без TODO. '
    "Верни ТОЛЬКО код Python, без markdown-обёрток."
)

REVIEW_SYSTEM = (
    "Ты — code reviewer. Проверь код и верни СТРОГО валидный JSON без markdown-обёрток:\n\n"
    "{\n"
    '  "ok": true/false,\n'
    '  "syntax_ok": true/false,\n'
    '  "has_main_block": true/false,\n'
    '  "imports_ok": true/false,\n'
    '  "issues": ["список проблем"],\n'
    '  "suggestions": ["список рекомендаций"]\n'
    "}\n\n"
    "Верни ТОЛЬКО JSON, без markdown-обёрток."
)


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    fence = re.search(r"```(?:python|json)?\s*\n?(.*?)```", t, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return t


def _safe_json_loads(text: str) -> dict[str, Any]:
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _make_llm(model: str, api_key: str, base_url: str, temperature: float) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )


# ---------- Звенья цепочки ----------

def analysis_chain(llm: ChatOpenAI, task_text: str) -> dict[str, Any]:
    """Звено 1: анализ задания -> структура."""
    chain = llm | StrOutputParser()
    raw = chain.invoke([
        SystemMessage(content=ANALYSIS_SYSTEM),
        HumanMessage(content=f"Техническое задание:\n```\n{task_text}\n```"),
    ])
    return _safe_json_loads(raw)


def tools_chain(llm: ChatOpenAI, analysis: dict[str, Any]) -> dict[str, Any]:
    """Звено 2: подбор инструментов для генерации."""
    chain = llm | StrOutputParser()
    raw = chain.invoke([
        SystemMessage(content=TOOLS_SYSTEM),
        HumanMessage(content=f"JSON-структура задачи:\n{json.dumps(analysis, ensure_ascii=False, indent=2)}"),
    ])
    return _safe_json_loads(raw)


def code_chain(llm: ChatOpenAI, analysis: dict[str, Any], tools: dict[str, Any]) -> str:
    """Звено 3: генерация полного Python-кода."""
    chain = llm | StrOutputParser()
    user_msg = (
        "Описание задачи:\n"
        f"{analysis.get('task_summary', '')}\n\n"
        "Структура (JSON):\n"
        f"{json.dumps(analysis, ensure_ascii=False, indent=2)}\n\n"
        "Инструменты (JSON):\n"
        f"{json.dumps(tools, ensure_ascii=False, indent=2)}\n\n"
        "Сгенерируй готовый Python-скрипт."
    )
    raw = chain.invoke([
        SystemMessage(content=CODE_SYSTEM),
        HumanMessage(content=user_msg),
    ])
    return _strip_code_fences(raw)


def review_chain(llm: ChatOpenAI, code: str) -> dict[str, Any]:
    """Звено 4: ревью через LLM."""
    chain = llm | StrOutputParser()
    raw = chain.invoke([
        SystemMessage(content=REVIEW_SYSTEM),
        HumanMessage(content=f"Код для проверки:\n```python\n{code}\n```"),
    ])
    return _safe_json_loads(raw)


def local_review(code: str) -> dict[str, Any]:
    """Локальная минимальная проверка: ast.parse + наличие main + импорты."""
    issues: list[str] = []
    suggestions: list[str] = []
    syntax_ok = False
    has_main = False
    imports_ok = False

    try:
        tree = ast.parse(code)
        syntax_ok = True
    except SyntaxError as e:
        issues.append(f"SyntaxError: {e}")
        return {
            "ok": False,
            "syntax_ok": False,
            "has_main_block": False,
            "imports_ok": False,
            "issues": issues,
            "suggestions": ["Исправить синтаксис"],
        }

    has_main = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in tree.body
    )
    if not has_main:
        issues.append('Нет блока if __name__ == "__main__"')
        suggestions.append('Добавить точку входа: if __name__ == "__main__": main()')

    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    imports_ok = len(imports) > 0
    if not imports_ok:
        suggestions.append("Добавить хотя бы один import (например, argparse)")

    ok = syntax_ok and has_main
    if ok:
        suggestions.append("Код прошёл минимальную проверку")

    return {
        "ok": ok,
        "syntax_ok": syntax_ok,
        "has_main_block": has_main,
        "imports_ok": imports_ok,
        "issues": issues,
        "suggestions": suggestions,
    }


def run_chain(
    task_text: str,
    *,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.2,
    do_review: bool = True,
) -> dict[str, Any]:
    """Запускает всю цепочку: analysis -> tools -> code -> (review)."""
    llm = _make_llm(model, api_key, base_url, temperature)

    analysis = analysis_chain(llm, task_text)
    tools = tools_chain(llm, analysis)
    code = code_chain(llm, analysis, tools)
    local = local_review(code)
    review = review_chain(llm, code) if do_review else None

    return {
        "analysis": analysis,
        "tools": tools,
        "code": code,
        "local_review": local,
        "review": review,
    }


def save_script(code: str, output_path: str | Path = "script.py") -> Path:
    """Сохраняет сгенерированный код в .py файл."""
    p = Path(output_path)
    p.write_text(code, encoding="utf-8")
    return p

