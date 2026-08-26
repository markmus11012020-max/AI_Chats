"""Загрузка и парсинг промптов из .md файлов.

Каждый файл содержит JSON внутри <code class="language-Markdown" ...>{...}</code>.
Извлекаем role (системный промпт) и метаданные.
"""
import json
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

FILES = {
    "summary": "Summary Prompt.md",
    "code": "Сode structure.md",
    "planning": "Task Planning Prompt.md",
    "base": None,  # базовый чат из ТЗ, system-промпт задаётся вручную
    "chains": None,  # роль для вкладки Chains; реальная логика в chains.py
}

LABELS = {
    "summary": "📝 Структурирование и анализ текста / Summary Prompt",
    "code": "💻 Генерация структуры кода / Code structure",
    "planning": "📋 Планирование задач проекта / Task Planning Prompt",
    "chains": "🔗 Генератор Python-кода (Chains)",
    "base": "💬 Базовый чат (ТЗ)",
}

BASE_SYSTEM_PROMPT = "Отвечай кратко и по делу."

_CODE_RE = re.compile(r"<code[^>]*>(.*?)</code>", re.DOTALL | re.IGNORECASE)


def _load_raw(path: Path) -> str:
    match = _CODE_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Не найден <code> блок в {path.name}")
    return match.group(1).strip()


def load_prompt(key: str) -> dict:
    if key == "base":
        return {
            "id": "base",
            "name": "Базовый чат (ТЗ)",
            "role": BASE_SYSTEM_PROMPT,
            "description": "Чат из исходного ТЗ: системный промпт «Отвечай кратко и по делу.»",
        }
    if key == "chains":
        return {
            "id": "chains",
            "name": "Генератор Python-кода (Chains)",
            "role": "Ты — генератор Python-кода. Описывай план решения по шагам.",
            "description": "Вкладка Chains: 4-звенная цепочка analysis → tools → code → review. Логика реализована в chains.py.",
        }
    path = PROMPTS_DIR / FILES[key]
    data = json.loads(_load_raw(path))
    return {
        "id": data.get("prompt_id", key),
        "name": data.get("name", key),
        "role": data["role"],
        "description": data.get("description", ""),
    }


def load_all() -> dict[str, dict]:
    return {key: load_prompt(key) for key in FILES}


def default_role() -> str:
    return load_prompt("summary")["role"]
