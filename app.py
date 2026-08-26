import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
from openai import OpenAI

from prompts import LABELS, default_role, load_all

API_KEY = os.getenv("ALLTOKENS_API_KEY", "")
BASE_URL = os.getenv("ALLTOKENS_BASE_URL", "https://alltokens.ru/api/v1")

MODELS = [
    "cohere/north-mini-code:free",
    "alltokens/pareto-code",
    "minimax/minimax-m3",
    "google/gemini-3-flash-preview",
    "openai/gpt-oss-20b:free",
    "anthropic/claude-haiku-4.5",
]

st.set_page_config(page_title="AllTokens Chat", page_icon="💬", layout="wide")

PROMPTS = load_all()
ROLE_KEYS = list(LABELS.keys())

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": default_role()}]
if "active_role" not in st.session_state:
    st.session_state.active_role = "summary"
if "model" not in st.session_state:
    st.session_state.model = MODELS[0]
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7
if "client" not in st.session_state:
    if not API_KEY:
        st.error("Не задан ALLTOKENS_API_KEY в .env")
        st.stop()
    st.session_state.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def apply_role(role_key: str) -> None:
    """Подставить системный промпт выбранной роли в начало истории."""
    new_system = PROMPTS[role_key]["role"]
    if st.session_state.messages and st.session_state.messages[0]["role"] == "system":
        st.session_state.messages[0]["content"] = new_system
    else:
        st.session_state.messages.insert(0, {"role": "system", "content": new_system})


with st.sidebar:
    st.title("⚙️ Настройки")
    st.session_state.model = st.selectbox(
        "Модель",
        MODELS,
        index=MODELS.index(st.session_state.model),
    )
    st.session_state.temperature = st.slider(
        "Температура",
        min_value=0.0,
        max_value=2.0,
        value=float(st.session_state.temperature),
        step=0.05,
        help="0 = точные ответы, 2 = максимально креативные",
    )
    if st.button("🗑️ Очистить чат"):
        st.session_state.messages = [{"role": "system", "content": PROMPTS[st.session_state.active_role]["role"]}]
        st.rerun()
    st.caption(f"Base URL: {BASE_URL}")

st.title("💬 Чат с ИИ")
st.caption(f"Модель: **{st.session_state.model}** · Температура: **{st.session_state.temperature}**")

tabs = st.tabs([LABELS[k] for k in ROLE_KEYS])
for tab, key in zip(tabs, ROLE_KEYS):
    with tab:
        prompt_info = PROMPTS[key]
        with st.expander("ℹ️ Описание роли", expanded=False):
            st.markdown(f"**{prompt_info['name']}**")
            st.caption(prompt_info["description"])
        if st.button(f"✅ Использовать эту роль", key=f"use_{key}", use_container_width=True):
            st.session_state.active_role = key
            apply_role(key)
            st.rerun()
        if st.session_state.active_role == key:
            st.success(f"Активная роль: {prompt_info['name']}")

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Введите сообщение..."):
    if not prompt.strip():
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = []
        try:
            stream = st.session_state.client.chat.completions.create(
                model=st.session_state.model,
                messages=st.session_state.messages,
                temperature=st.session_state.temperature,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    full_response.append(delta)
                    placeholder.markdown("".join(full_response) + "▌")
            response_text = "".join(full_response)
            placeholder.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
        except Exception as e:
            placeholder.error(f"Ошибка API: {type(e).__name__}: {e}")
            if getattr(e, "response", None) is not None:
                try:
                    placeholder.error(f"status={e.response.status_code}")
                except Exception:
                    pass
            if st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()