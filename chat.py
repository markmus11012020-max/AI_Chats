import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI

API_KEY = os.getenv("ALLTOKENS_API_KEY", "")
BASE_URL = os.getenv("ALLTOKENS_BASE_URL", "https://alltokens.ru")

MODELS = [
    "cohere/north-mini-code:free",
    "alltokens/pareto-code",
    "minimax/minimax-m3",
    "google/gemini-3-flash-preview",
    "openai/gpt-oss-20b:free",
    "anthropic/claude-haiku-4.5",
]


def select_model() -> str:
    print("=== Выбор модели ===")
    for i, m in enumerate(MODELS, 1):
        print(f"{i}. {m}")
    while True:
        choice = input("Номер модели: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(MODELS):
            return MODELS[int(choice) - 1]
        print("Некорректный выбор. Попробуйте снова.")


def main() -> None:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    model = select_model()
    print(f"\nВыбрана модель: {model}\nДля выхода введите: exit\n")

    messages = [
        {"role": "system", "content": "Отвечай кратко и по делу."}
    ]

    while True:
        try:
            user_input = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nЗавершение.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Завершение.")
            break

        messages.append({"role": "user", "content": user_input})

        print("ИИ: ", end="", flush=True)
        full_response_parts = []
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    print(delta, end="", flush=True)
                    full_response_parts.append(delta)
        except Exception as e:
            print(f"\n[Ошибка API: {type(e).__name__}: {e}]", file=sys.stderr)
            if getattr(e, "response", None) is not None:
                try:
                    print(f"  status={e.response.status_code} body={e.response.text}", file=sys.stderr)
                except Exception:
                    pass
            if getattr(e, "__cause__", None):
                import traceback
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            if messages and messages[-1]["role"] == "user":
                messages.pop()
            continue

        print()
        messages.append({
            "role": "assistant",
            "content": "".join(full_response_parts),
        })


if __name__ == "__main__":
    if not API_KEY:
        print("Не задан API-ключ. Установите переменную окружения ALLTOKENS_API_KEY.", file=sys.stderr)
        sys.exit(1)
    main()