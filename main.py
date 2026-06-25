import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, ImageTk, Image
from pathlib import Path
import ctypes
import platform
import requests
import shutil
from functools import partial
from dotenv import load_dotenv
import os
from src.ocr.ocr_component import get_anki_tags_from_image
from src.utils import get_latest_file, get_today_ymd, convert_file_to_base64

# .env ファイルを読み込む
load_dotenv()

# 設定値を取得
TESSERACT_PATH = os.getenv("TESSERACT_PATH")
ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL")


CAPTURE_PATH = Path(__file__).resolve().parents[0] / "capture"
COMPLETED_PATH = CAPTURE_PATH / "completed"

APP_WIDTH = 670
APP_HEIGHT = 450
WINDOWS_TASKBAR_SIZE = 88

IMAGE_AREA_SCALE = 0.75
IMAGE_WIDTH_AREA = int(APP_WIDTH * IMAGE_AREA_SCALE)
IMAGE_HEIGHT_AREA = int(APP_HEIGHT * IMAGE_AREA_SCALE)
MARGIN_SCALE = 5

CAPTURE_TARGET_QUESTION = "question"
CAPTURE_TARGET_ANSWER = "answer"

STATE_WAITING_QUESTION = 0
STATE_WAITING_ANSWER = 1
STATE_READY_TO_REGISTER = 2

WHITE = "white"
BLUE = "blue"


# ==========================================
# 1. DPIスケール（拡大率）のずれを防ぐ設定
# ==========================================
if platform.system() == "Windows":
    try:
        # Windows 8.1以降向けのDPI認識設定（高精度）
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        # 古いWindows向けのフォールバック
        ctypes.windll.user32.SetProcessDPIAware()


class App(tk.Tk):
    """アプリ全体のウィンドウ管理とメイン画面表示を担う Tk ルート。"""

    def __init__(self):
        super().__init__()
        self.title("AnkiSnapImporter")
        self.geometry(self.default_main_window_position())

        self.main_frame = MainLayer(self)
        self.main_frame.pack(fill="both", expand=True)

    def default_main_window_position(self):
        """メインウィンドウの初期サイズ文字列を返す。"""
        x_position = self.winfo_screenwidth() - APP_WIDTH
        y_position = self.winfo_screenheight() - APP_HEIGHT - WINDOWS_TASKBAR_SIZE

        return f"{APP_WIDTH}x{APP_HEIGHT}+{x_position}+{y_position}"
        # return f"{APP_WIDTH}x{APP_HEIGHT}"

    def show_main_window(self):
        """撮影モード終了後に通常ウィンドウ表示へ戻す。"""
        self.attributes("-fullscreen", False)
        self.attributes("-alpha", 1.0)
        self.configure(bg="SystemButtonFace")


class MainLayer(tk.Frame):
    """メイン操作画面。"""

    def __init__(self, root):
        super().__init__(master=root, bg="White")
        self.root = root
        self.question_path = None
        self.answer_path = None
        self.state = STATE_WAITING_QUESTION

        self.root.bind("<F5>", self.on_screenshot_hotkey)
        self.root.bind("<Control-s>", self.on_register_hotkey)

        self.images = []
        self.create_widgets()
        self.pack(fill="both", expand=True)

    def create_widgets(self):
        """画面に必要なウィジェットを生成・配置する。"""

        # リサイズ時の列の伸縮・均等配置設定
        for i in range(2):
            self.columnconfigure(i, weight=1, uniform="buttons")

        # リサイズ時に画像プレビューエリア（行1）を縦に広げる設定
        self.grid_rowconfigure(1, weight=1)

        # スクリーンショット撮影ボタンの配置
        self.btn_question = self.create_screenshot_button(
            0, "問題を撮影(F5)", STATE_WAITING_QUESTION
        )
        self.btn_answer = self.create_screenshot_button(
            1, "解答を撮影(F5)", STATE_WAITING_ANSWER
        )

        # 画像プレビューエリアの配置
        self.preview_question = self.create_image_area(0, self.question_path)
        self.preview_answer = self.create_image_area(1, self.answer_path)

        # 再撮影ボタンの配置
        self.btn_reshooting_question = self.create_reshooting_button(
            0, "問題を再撮影", STATE_WAITING_QUESTION, CAPTURE_TARGET_QUESTION
        )
        self.btn_reshooting_answer = self.create_reshooting_button(
            1, "解答を再撮影", STATE_WAITING_ANSWER, CAPTURE_TARGET_ANSWER
        )
        # Anki登録ボタンの配置
        self.btn_anki_register = self.create_anki_register_button()

    def on_screenshot_hotkey(self, event):
        """F5キー押下時にスクリーンショット撮影モードを開始する。"""

        if self.state == STATE_READY_TO_REGISTER:
            return "break"

        capture_target = (
            CAPTURE_TARGET_QUESTION
            if self.state == STATE_WAITING_QUESTION
            else CAPTURE_TARGET_ANSWER
        )

        self.show_screenshot(capture_target)

    def on_register_hotkey(self, event):
        """Ctrl+sキー押下時にAnki登録を開始する。"""

        if self.state != STATE_READY_TO_REGISTER:
            return "break"

        self.on_click_anki_register()

    def create_screenshot_button(self, column, text_name, state):
        """指定列に撮影ボタンを作成し、状態に応じて有効/無効を設定する。"""
        btn_screenshot = tk.Button(self)
        btn_screenshot["text"] = text_name
        btn_screenshot["command"] = lambda s=state: self.on_click_screenshot(s)
        btn_screenshot["state"] = "normal" if self.state == state else "disabled"

        btn_screenshot.grid(row=0, column=column, padx=1, sticky="we")
        return btn_screenshot

    def create_image_area(self, column, image_path):
        """画像プレビュー用のキャンバスを作成して配置する。"""

        image_area = tk.Canvas(
            self, width=IMAGE_WIDTH_AREA, height=IMAGE_HEIGHT_AREA, bg="Black"
        )

        kind = "question" if column == 0 else "answer"
        image_area.bind(
            "<Configure>",
            partial(self.on_resize, canvas=image_area, kind=kind),
        )

        if not image_path:
            image_area.create_rectangle(
                MARGIN_SCALE,
                MARGIN_SCALE,
                APP_WIDTH - MARGIN_SCALE,
                APP_HEIGHT - MARGIN_SCALE,
                dash=(5, 5),
                fill=WHITE,
            )
            image_area.create_text(
                APP_WIDTH / 2,
                APP_HEIGHT / 2,
                text="No Image",
                fill="black",
                font=("Meiryo", 16),
            )

        else:
            self.draw_resized_image_on_canvas(
                image_path,
                image_area,
                IMAGE_WIDTH_AREA,
                IMAGE_HEIGHT_AREA,
            )

        image_area.grid(row=1, column=column, sticky="nsew")
        return image_area

    def create_reshooting_button(self, column, text_name, state, capture_target):
        """指定列に撮影ボタンを作成し、状態に応じて有効/無効を設定する。"""
        btn_screenshot = tk.Button(self)
        btn_screenshot["text"] = text_name
        btn_screenshot["command"] = lambda c=capture_target: self.on_click_reshooting(c)
        if capture_target == CAPTURE_TARGET_QUESTION:
            btn_screenshot["state"] = (
                "normal"
                if self.state in (STATE_WAITING_ANSWER, STATE_READY_TO_REGISTER)
                else "disabled"
            )
        elif capture_target == CAPTURE_TARGET_ANSWER:
            btn_screenshot["state"] = (
                "normal" if state == STATE_READY_TO_REGISTER else "disabled"
            )

        btn_screenshot.grid(row=2, column=column, padx=1, sticky="we")
        return btn_screenshot

    def create_anki_register_button(self):
        """Anki登録ボタンを作成し、現在状態に応じて活性を切り替える。"""
        btn_anki_register = tk.Button(self)
        btn_anki_register["text"] = "Ankiに登録(Ctrl+s)"
        btn_anki_register["height"] = 2
        btn_anki_register["command"] = self.on_click_anki_register
        btn_anki_register["state"] = (
            "normal" if self.state == STATE_READY_TO_REGISTER else "disabled"
        )

        btn_anki_register.grid(row=3, column=0, columnspan=2, sticky="nsew")

        return btn_anki_register

    def on_resize(self, event, canvas, kind):
        """キャンバスのサイズ変更時に、画像を新しい領域へ再描画する。"""
        if kind == "question":
            image_path = self.question_path
        else:
            image_path = self.answer_path

        if not image_path:
            self.redraw_rectangle(canvas, event.width, event.height)
        else:
            self.redraw_image(canvas, image_path, event.width, event.height)

    def redraw_rectangle(self, canvas, width, height):
        """キャンバスのサイズ変更時に、余白付きの選択枠を再描画する。"""
        canvas.delete("all")
        rect_width = width - MARGIN_SCALE
        rect_height = height - MARGIN_SCALE

        canvas.create_rectangle(
            MARGIN_SCALE,
            MARGIN_SCALE,
            rect_width,
            rect_height,
            outline=BLUE,
            fill=WHITE,
        )

        self.redraw_text(canvas, width, height)

    def redraw_text(self, canvas, width, height):
        """キャンバスのサイズ変更時に、テキストを再描画する。"""
        center_x = width // 2
        center_y = height // 2

        canvas.create_text(
            center_x, center_y, text="No Image", fill="black", font=("Meiryo", 16)
        )

    def redraw_image(self, canvas, image_path, width, height):
        """指定サイズに合わせてキャンバス上の画像を描き直す。"""
        canvas.delete("all")
        self.draw_resized_image_on_canvas(image_path, canvas, width, height)

    def draw_resized_image_on_canvas(
        self, image_path, canvas, image_width_area, image_height_area
    ):
        """画像を比率維持でリサイズし、キャンバス中央へ描画する。"""

        # 画像を開く
        original_image = Image.open(image_path)
        w, h = original_image.width, original_image.height

        # アスペクト比を維持したまま表示領域に収まるスケールを計算
        fit_scale = min(image_width_area / w, image_height_area / h)

        # 画像をリサイズ
        resized_image = original_image.resize((int(w * fit_scale), int(h * fit_scale)))
        photo_image = ImageTk.PhotoImage(resized_image)
        self.images.append(photo_image)

        # 中央配置の座標を計算
        x = (image_width_area - resized_image.width) // 2
        y = (image_height_area - resized_image.height) // 2

        canvas.create_image(
            x,
            y,
            anchor="nw",
            image=photo_image,
        )

    def on_click_screenshot(self, state):
        """撮影ボタン押下時にスクリーンショットレイヤーを表示する。"""

        capture_target = (
            CAPTURE_TARGET_QUESTION
            if state == STATE_WAITING_QUESTION
            else CAPTURE_TARGET_ANSWER
        )

        self.show_screenshot(capture_target)

    def on_click_reshooting(self, capture_target):
        """最撮影ボタン押下時にスクリーンショットレイヤーを表示する。"""
        self.show_screenshot(capture_target, True)

    def show_screenshot(self, capture_target, is_recapture=False):
        """メイン画面を隠してスクリーンショット用レイヤーへ遷移する。"""

        self.pack_forget()
        screen_layer = ScreenShotLayer(self.root, capture_target, is_recapture)
        screen_layer.pack(fill="both", expand=True)

    def on_click_anki_register(self):
        """最新の問題/解答画像をAnkiへメディア登録し、ノートを追加する。"""
        deck_name = "応用情報技術者試験"
        # 最新の問題・解答データのファイルパスを取得する
        question, answer = get_latest_file(CAPTURE_PATH)
        anki_tag_set = set()

        for file_path in (self.question_path, self.answer_path):

            # Ankiのメディアフォルダへコピーする
            file_data = convert_file_to_base64(file_path)
            self.request_anki_connect(
                "storeMediaFile", filename=file_path.name, data=file_data
            )

            # Ankiの登録用のタグ情報を取得する
            anki_tag_set.update(get_anki_tags_from_image(file_path))
            anki_tags = list(anki_tag_set)

        # 問題・解答をAnkiに追加する
        self.add_question(deck_name, question.name, answer.name, tags=anki_tags)

        # 問題・解答を完了ディレクトリに移動する
        for file in (self.question_path, self.answer_path):
            self.move_to_completed(file)

        # ステータスを問題待機状態に更新
        self.state = STATE_WAITING_QUESTION
        self.update_button_state()

        # プレビューを初期状態に戻す
        self.question_path = None
        self.answer_path = None
        self.redraw_rectangle(
            self.preview_question,
            self.preview_question.winfo_width(),
            self.preview_question.winfo_height(),
        )
        self.redraw_rectangle(
            self.preview_answer,
            self.preview_answer.winfo_width(),
            self.preview_answer.winfo_height(),
        )

        messagebox.showinfo("完了", f"Ankiに問題を登録しました")

    def request_anki_connect(self, action, **params):
        """AnkiConnect APIへリクエストを送り、結果JSONを返す。"""
        try:
            response = requests.post(
                ANKI_CONNECT_URL,
                json={"action": action, "params": params, "version": 6},
            )

            # 接続の確認
            response.raise_for_status()

            result = response.json()

            if result["error"] is not None:
                raise RuntimeError(result["error"])

            return result

        except requests.exceptions.ConnectionError as e:
            messagebox.showerror("登録エラー", "Ankiが起動していません")
            raise RuntimeError("Ankiが起動していません")

    def add_question(self, deck_name, front, back, tags=None):
        """指定デッキへ画像付きの基本ノートを1件追加する。"""
        if tags is None:
            tags = []

        self.request_anki_connect("createDeck", deck=deck_name)

        return self.request_anki_connect(
            "addNote",
            note={
                "deckName": deck_name,
                "modelName": "基本",
                "fields": {
                    "表面": f"<img src='{front}'>",
                    "裏面": f"<img src='{back}'>",
                },
                "tags": tags,
            },
        )

    def move_to_completed(self, file):
        """撮影ファイルを完了ディレクトリに移動する。"""
        shutil.move(file, COMPLETED_PATH)

    def update_button_state(self):
        """現在の状態に合わせて各操作ボタンの有効状態を更新する。"""
        self.btn_question["state"] = (
            "normal" if self.state == STATE_WAITING_QUESTION else "disabled"
        )

        self.btn_answer["state"] = (
            "normal" if self.state == STATE_WAITING_ANSWER else "disabled"
        )

        self.btn_anki_register["state"] = (
            "normal" if self.state == STATE_READY_TO_REGISTER else "disabled"
        )

        self.btn_reshooting_question["state"] = (
            "normal"
            if self.state in (STATE_WAITING_ANSWER, STATE_READY_TO_REGISTER)
            else "disabled"
        )

        self.btn_reshooting_answer["state"] = (
            "normal" if self.state == STATE_READY_TO_REGISTER else "disabled"
        )


class ScreenShotLayer(tk.Canvas):
    """画面上でドラッグ選択を受け付け、指定範囲を画像として保存するレイヤー。"""

    def __init__(self, root, capture_target, is_recapture):
        super().__init__(master=root)
        self.root = root
        self.rect_id = None
        self.config(bg="Gray")
        self.border_width = 10
        self.reset_coordinate()

        # ウィンドウのフルスクリーン・半透明化
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.5)

        # イベントのバインド
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind(
            "<ButtonRelease-1>",
            lambda e: self.on_release(e, capture_target, is_recapture),
        )
        self.bind("<ButtonPress-3>", self.on_screenshot_cancel)

    def reset_coordinate(self):
        """ドラッグ開始/終了座標を初期化する。"""
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

    def on_press(self, event):
        """ドラッグ開始位置を記録する。"""
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event):
        """ドラッグ中の終点を更新し、選択矩形を描画する。"""
        self.end_x = event.x
        self.end_y = event.y
        self.create_screenshot_area()

    def on_release(self, event, capture_target, is_recapture):
        """ドラッグ終了時に撮影を実行し、メイン画面へ復帰する。"""
        self.end_x = event.x
        self.end_y = event.y

        # 単クリックによる誤撮影を防ぐため、選択範囲なしなら中断
        if self.start_x == self.end_x and self.start_y == self.end_y:
            return "break"

        # スクリーンショット先のファイルパスを取得
        screenshot_filepath = self.create_filepath(capture_target)

        # スクリーンショットの実施
        self.screenshot(screenshot_filepath)

        self.destroy()
        self.root.show_main_window()

        # ファイルパス更新
        if capture_target == CAPTURE_TARGET_QUESTION:
            self.root.main_frame.question_path = screenshot_filepath
            self.root.main_frame.redraw_image(
                self.root.main_frame.preview_question,
                self.root.main_frame.question_path,
                self.root.main_frame.preview_question.winfo_width(),
                self.root.main_frame.preview_question.winfo_height(),
            )

        elif capture_target == CAPTURE_TARGET_ANSWER:
            self.root.main_frame.answer_path = screenshot_filepath
            self.root.main_frame.redraw_image(
                self.root.main_frame.preview_answer,
                self.root.main_frame.answer_path,
                self.root.main_frame.preview_answer.winfo_width(),
                self.root.main_frame.preview_answer.winfo_height(),
            )

        # ステータスの更新（再撮影時はスキップ）
        if not is_recapture:
            if self.root.main_frame.state == STATE_WAITING_QUESTION:
                self.root.main_frame.state = STATE_WAITING_ANSWER
            elif self.root.main_frame.state == STATE_WAITING_ANSWER:
                self.root.main_frame.state = STATE_READY_TO_REGISTER

        # ボタンの有効化・無効化
        self.root.main_frame.update_button_state()

        self.root.main_frame.pack(fill="both", expand=True)

    def on_screenshot_cancel(self, event):
        """右クリックでスクリーンショット撮影をキャンセルし、メイン画面へ戻る。"""
        self.destroy()
        self.root.show_main_window()
        self.root.main_frame.pack(fill="both", expand=True)

    def create_screenshot_area(self):
        """現在の開始点/終点に基づいて選択矩形を再描画する。"""
        if self.rect_id:
            self.delete(self.rect_id)

        self.rect_id = self.create_rectangle(
            self.start_x,
            self.start_y,
            self.end_x,
            self.end_y,
            outline=BLUE,
            width=self.border_width,
            fill="white",
        )

    def screenshot(self, file_path):
        """選択範囲をキャプチャし、種別に応じたファイル名で保存する。"""
        x1 = min(self.start_x, self.end_x) + self.border_width
        y1 = min(self.start_y, self.end_y) + self.border_width
        x2 = max(self.start_x, self.end_x) - self.border_width
        y2 = max(self.start_y, self.end_y) - self.border_width

        # スクリーンショットレイヤーを一時的に非表示にする
        self.root.withdraw()

        try:
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img.save(file_path)
            messagebox.showinfo("完了", "保存しました")
        except Exception as e:
            messagebox.showerror(
                "撮影エラー", f"スクリーンショット取得に失敗しました\n{e}"
            )

        # スクリーンショットレイヤーを再表示する
        self.root.deiconify()

    def create_filepath(self, capture_target):
        """当日分の連番を考慮した保存ファイル名を生成する。"""

        # 今日日付のファイルの一覧を取得
        today = get_today_ymd()
        today_files = self.get_today_file_list(f"{capture_target}*.png")

        if not today_files:
            file_name = f"{today}_{capture_target}_001.png"
        else:
            last_file = today_files[-1]
            last_number = int(last_file.split("_")[-1])

            file_name = f"{today}_{capture_target}_{last_number + 1:03d}.png"

        return CAPTURE_PATH / file_name

    def get_today_file_list(self, file_pattern):
        """当日分の撮影フォルダと完了フォルダから、指定ファイル名パターンに一致するファイル一覧を返す。"""
        today = get_today_ymd()

        files = set()
        files.update(Path(CAPTURE_PATH).glob(f"*{today}*{file_pattern}"))
        files.update(Path(COMPLETED_PATH).glob(f"*{today}*{file_pattern}"))

        # ファイル名のみでリスト化してソート
        sorted_files = sorted(list(file.stem for file in files))

        return sorted_files


if __name__ == "__main__":
    app = App()
    app.mainloop()
