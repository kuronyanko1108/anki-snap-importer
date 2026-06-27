from PIL import Image
import pyocr
import pyocr.builders
from janome.tokenizer import Tokenizer
import json
from dotenv import load_dotenv
import os
from pathlib import Path

# .env ファイルを読み込む
load_dotenv()

# 設定値を取得
TESSERACT_PATH = os.getenv("TESSERACT_PATH")

# プロジェクトルート配下の設定ファイルパス
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
USER_DICT_PATH = CONFIG_DIR / "user_dict.csv"
TAG_CONFIG_PATH = CONFIG_DIR / "config.json"


def get_anki_tags_from_image(fale_path: str | Path) -> list[str]:
    """画像をOCRしてAnki用タグを抽出する。

    Args:
        fale_path: OCR対象画像のファイルパス。

    Returns:
        抽出されたAnkiタグのリスト。
    """
    # Tesseractの実行ファイルへのパスを指定
    pyocr.tesseract.tesseract_cmd = TESSERACT_PATH

    # OCRエンジンの選択
    tools = pyocr.get_available_tools()
    tool = tools[0]

    # 画像のファイルを指定する
    img = Image.open(fale_path)

    # 画像からテキストを抽出
    builder = pyocr.builders.TextBuilder(tesseract_layout=6)
    txt = tool.image_to_string(img, lang="eng+jpn", builder=builder).replace(" ", "")

    # 形態素解析
    t = Tokenizer(str(USER_DICT_PATH), udic_type="simpledic", udic_enc="utf8")
    words_set = set(token for token in t.tokenize(txt, wakati=True))

    # JSONファイルの読み込み
    with open(TAG_CONFIG_PATH, mode="r", encoding="utf-8") as f:
        tag_mapping: dict[str, list[str]] = json.load(f)

    # タグの設定
    tag_set = set()
    for word in words_set:
        if word in tag_mapping:
            tag_set.update(tag_mapping[word])

    anki_tags = list(tag_set)

    return anki_tags
