import datetime
from pathlib import Path
import base64


class UtilsException(Exception):
    pass


def get_today_ymd() -> str:
    """今日日付を YYYYMMDD 形式の文字列で返す。"""
    return datetime.date.today().strftime("%Y%m%d")


def get_latest_file(folder_path: Path) -> tuple[Path, Path]:
    """当日分の最新の問題画像と解答画像のパスを返す。"""
    today = get_today_ymd()

    latest_question_files = sorted(Path(folder_path).glob(f"*{today}*question*.png"))
    latest_answer_files = sorted(Path(folder_path).glob(f"*{today}*answer*.png"))

    if not latest_question_files:
        raise UtilsException("問題データを取得できませんでした。")

    if not latest_answer_files:
        raise UtilsException("解答データを取得できませんでした。")

    return latest_question_files[-1], latest_answer_files[-1]


def convert_file_to_base64(file_path: Path) -> str:
    """指定したファイルをBase64文字列へ変換して返す。"""
    with open(file_path, "rb") as f:
        return base64.b64encode((f.read())).decode()
