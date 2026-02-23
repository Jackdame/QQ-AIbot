import logging
import os

from config import MEMORY_DIR


def get_memory_path(user_id):
    return os.path.join(MEMORY_DIR, f"mem_{user_id}.txt")


def search_memory(user_id, user_text):
    path = get_memory_path(user_id)
    if not os.path.exists(path):
        return ""

    try:
        with open(path, "r", encoding="utf-8") as f:
            facts = f.read().strip()
        return f"【已知背景信息】：\n{facts}" if facts else ""
    except Exception as e:
        logging.warning("Failed to read memory file for user %s: %s", user_id, e)
        return ""