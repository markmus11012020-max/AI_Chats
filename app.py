import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
from openai import OpenAI

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

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "Отвечай кратко и по делу."}]
if "model" not in st.session_state:
    st.session_state.model = MODELS[0]
if "client" not in st.session_state:
    if not API_KEY:
        st.error("Не задан ALLTOKENS_API_KEY в .env")
        st.stop()
    st.session_state.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

with st.sidebar:
    st.title("⚙️ Настройки")
    st.session_state.model = st.selectbox(
        "Модель",
        MODELS,
        index=MODELS.index(st.session_state.model),
    )
    if st.button("🗑️ Очистить чат"):
        st.session_state.messages = [{"role": "system", "content": "Отвечай кратко и по делу."}]
        st.rerun()
    st.caption(f"Base URL: {BASE_URL}")

st.title("💬 Чат с ИИ")
st.caption(f"Модель: **{st.session_state.model}**")

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