import argparse
import json
import logging
from pathlib import Path

DELETE_PATTERNS = [
    "我给你发了一个红包，赶紧去拆!",
    "收到红包，请在手机端查看",
    "[语音通话]",
    "已在其他设备接听",
    "该消息已撤回",
]

STRIP_PATTERNS = [
    "[语音转文字]",
    "［语音转文字］",
    "语音转文字",
    "[图片]",
    "[表情]",
    "链接",
    "[]",
]


def is_noisy_row(text):
    return any(p in text for p in DELETE_PATTERNS)


def strip_noise(text):
    for p in STRIP_PATTERNS:
        text = text.replace(p, "")
    return text


def get_text(data):
    return "".join(msg.get("value", "") for msg in data.get("conversations", []))


def clean(input_path, output_path, max_length):
    kept = dropped_noise = dropped_long = dropped_empty = dropped_invalid = 0

    with input_path.open("r", encoding="utf-8") as fin, \
         output_path.open("w", encoding="utf-8") as fout:

        for raw in fin:
            line = raw.strip()
            if not line:
                continue

            if is_noisy_row(line):
                dropped_noise += 1
                continue

            line = strip_noise(line)

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                dropped_invalid += 1
                continue

            text = get_text(data)
            if not text.strip():
                dropped_empty += 1
                continue

            if len(text) > max_length:
                dropped_long += 1
                continue

            fout.write(json.dumps(data, ensure_ascii=False) + "\n")
            kept += 1

    logging.info("kept=%d  noise=%d  too_long=%d  empty=%d  invalid=%d",
                 kept, dropped_noise, dropped_long, dropped_empty, dropped_invalid)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="my_data.jsonl")
    parser.add_argument("--output", default="new_data.jsonl")
    parser.add_argument("--max-length", type=int, default=800)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    clean(Path(args.input), Path(args.output), args.max_length)