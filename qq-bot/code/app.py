import logging
import os
import uuid

import requests
from flask import Flask, request, jsonify

from ai import get_ollama_response
from config import BOT_QQ_ID, MEME_DIR, NAPCAT_GROUP_URL, NAPCAT_PRIVATE_URL

app = Flask(__name__)

MIN_IMAGE_SIZE = 5 * 1024
MAX_IMAGE_SIZE = 2 * 1024 * 1024


def steal_meme(raw_msg):
    """下载后至本地库，进而引用"""
    if not isinstance(raw_msg, list):
        return
    try:
        for item in raw_msg:
            if item.get("type") != "image":
                continue
            img_url = item.get("data", {}).get("url")
            if not img_url:
                continue
            img_data = requests.get(img_url, timeout=10).content
            if not (MIN_IMAGE_SIZE <= len(img_data) <= MAX_IMAGE_SIZE):
                continue
            filename = f"stolen_{uuid.uuid4().hex[:8]}.jpg"
            with open(os.path.join(MEME_DIR, filename), "wb") as f:
                f.write(img_data)
            logging.info("Saved meme: %s", filename)
    except Exception as e:
        logging.warning("Failed to steal meme: %s", e)


def parse_message(raw_msg):
    """Return (is_at_me, clean_text) from a raw message."""
    is_at_me = False
    text = ""

    if isinstance(raw_msg, list):
        for item in raw_msg:
            if item.get("type") == "at" and str(item.get("data", {}).get("qq")) == str(BOT_QQ_ID):
                is_at_me = True
            if item.get("type") == "text":
                text += item["data"].get("text", "")
    else:
        at_code = f"[CQ:at,qq={BOT_QQ_ID}]"
        raw_str = str(raw_msg)
        if at_code in raw_str:
            is_at_me = True
            text = raw_str.replace(at_code, "").strip()
        else:
            text = raw_str

    return is_at_me, text


def send_reply(message_type, user_id, group_id, reply_text):
    try:
        if message_type == "private":
            requests.post(NAPCAT_PRIVATE_URL, json={
                "user_id": int(user_id),
                "message": reply_text
            }, timeout=10)
        elif message_type == "group":
            requests.post(NAPCAT_GROUP_URL, json={
                "group_id": int(group_id),
                "message": f"[CQ:at,qq={user_id}] {reply_text}"
            }, timeout=10)
    except Exception as e:
        logging.warning("Failed to send reply to NapCat: %s", e)


@app.route("/", methods=["POST"])
def qq_webhook():
    data = request.json
    if not data or data.get("post_type") != "message":
        return jsonify({"status": "ignored"})

    raw_msg = data.get("message")
    steal_meme(raw_msg)

    message_type = data.get("message_type")
    user_id = data.get("user_id")
    group_id = data.get("group_id")

    is_at_me, clean_msg = parse_message(raw_msg)

    should_reply = (message_type == "private") or (message_type == "group" and is_at_me)
    if not should_reply or not clean_msg.strip():
        return jsonify({"status": "ignored"})

    logging.info("Received from %s: %s", user_id, clean_msg)
    reply_text = get_ollama_response(user_id, clean_msg)
    logging.info("Replying to %s: %s", user_id, reply_text)

    send_reply(message_type, user_id, group_id, reply_text)
    return jsonify({"status": "success"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(host="0.0.0.0", port=5000)