import logging
import os
import random
import re
from datetime import datetime, timedelta, timezone

import requests

from config import MEME_DIR, MODEL_NAME, OLLAMA_API, SYSTEM_PROMPT
from memory import search_memory

MEME_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
FALLBACK_FACE = "[CQ:face,id=9]"
MAX_CONTEXT = 9  

session_data = {}
last_replies = {}


def get_random_meme():
    try:
        if not os.path.exists(MEME_DIR):
            os.makedirs(MEME_DIR)
        files = [f for f in os.listdir(MEME_DIR)
                 if os.path.splitext(f)[1].lower() in MEME_EXTENSIONS]
        if not files:
            logging.warning("No memes found in %s", MEME_DIR)
            return FALLBACK_FACE
        abs_path = os.path.abspath(os.path.join(MEME_DIR, random.choice(files)))
        formatted = abs_path.replace("\\", "/")
        if not formatted.startswith("/"):
            formatted = "/" + formatted
        return f"[CQ:image,file=file://{formatted}]"
    except Exception as e:
        logging.warning("Failed to load meme: %s", e)
        return FALLBACK_FACE


def apply_meme_strategy(reply):
    if random.random() < 0.05:
        return get_random_meme()
    clean = re.sub(r'\[CQ:.*?\]', '', reply).strip()
    return clean if clean else get_random_meme()


def build_system_message():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    time_str = now.strftime(f"%Y-%m-%d %H:%M {weekdays[now.weekday()]}")
    return f"【当前时间】：{time_str}\n{SYSTEM_PROMPT}"


def get_ollama_response(user_id, user_text):
    memory_context = search_memory(user_id, user_text)
    system_content = build_system_message() + "\n" + memory_context
    system_msg = {"role": "system", "content": system_content}

    if user_id not in session_data:
        session_data[user_id] = [system_msg]
    else:
        session_data[user_id][0] = system_msg

    session_data[user_id].append({"role": "user", "content": str(user_text)})

    if len(session_data[user_id]) > MAX_CONTEXT:
        session_data[user_id] = [session_data[user_id][0]] + session_data[user_id][-8:]

    payload = {
        "model": MODEL_NAME,
        "messages": session_data[user_id],
        "stream": False,
        "options": {"temperature": 0.9, "top_p": 0.9, "num_predict": 150}
    }

    try:
        r = requests.post(OLLAMA_API, json=payload, timeout=90)
        r.raise_for_status()

        raw = r.json()["message"]["content"].strip()
        wants_meme = bool(re.search(r'\[meme\]', raw, re.IGNORECASE))
        raw = re.sub(r'\[.*?\]', '', raw).strip()

        if wants_meme or not raw:
            final = get_random_meme()
        elif last_replies.get(user_id) == raw:
            logging.debug("Repeat detected for %s, sending meme instead.", user_id)
            final = get_random_meme()
        else:
            final = apply_meme_strategy(raw)

        last_replies[user_id] = raw
        session_data[user_id].append({"role": "assistant", "content": final})
        return final

    except Exception as e:
        logging.warning("Ollama request failed: %s", e)
        return "请求失败"