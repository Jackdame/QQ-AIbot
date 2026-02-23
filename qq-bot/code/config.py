import os
OLLAMA_API = ""
MODEL_NAME = "" 
NAPCAT_PRIVATE_URL = ""
NAPCAT_GROUP_URL = ""
BOT_QQ_ID = 填你的qq号

MEMORY_DIR = r""
os.makedirs(MEMORY_DIR, exist_ok=True)
MEME_DIR = r""
if not os.path.exists(MEME_DIR):
    os.makedirs(MEME_DIR)
SYSTEM_PROMPT = (
    """
    人设提示词。
    """
)