from ..utils import get_today_ymd
from pathlib import Path
from PIL import ImageGrab

CAPTURE_PATH = Path(__file__).resolve().parents[2] / "capture"
COMPLETED_PATH = CAPTURE_PATH / "completed"


def screenshot(file_path: Path, bbox: tuple[int, int, int, int]) -> None:
    """指定 bbox の範囲をキャプチャし、file_path に保存する。"""
    img = ImageGrab.grab(bbox=bbox)
    img.save(file_path)


def create_filepath(capture_target: str) -> Path:
    """当日分の連番を考慮した保存ファイル名を生成する。"""

    # 今日日付のファイルの一覧を取得
    today = get_today_ymd()
    today_file_name_list = get_today_file_list(f"{capture_target}*.png")

    if not today_file_name_list:
        file_name = f"{today}_{capture_target}_001.png"
    else:
        last_file_name = today_file_name_list[-1]
        file_number = int(last_file_name.split("_")[-1])

        file_name = f"{today}_{capture_target}_{file_number + 1:03d}.png"

    return CAPTURE_PATH / file_name


def get_today_file_list(file_pattern: str) -> list:
    """当日分の撮影フォルダと完了フォルダから、指定ファイル名パターンに一致するファイル一覧を返す。"""
    today = get_today_ymd()

    files: set[Path] = set()
    files.update(Path(CAPTURE_PATH).glob(f"*{today}*{file_pattern}"))
    files.update(Path(COMPLETED_PATH).glob(f"*{today}*{file_pattern}"))

    # ファイル名のみでリスト化してソート
    sorted_files = sorted(list(file.stem for file in files))

    return sorted_files
