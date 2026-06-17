import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, ImageTk, Image
from pathlib import Path
import ctypes
import platform
import requests

from src import utils

path = Path.cwd() / "capture"
APP_WIDTH = 900
APP_HEIGHT = 450

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
        self.title("anki_snap_importer")
        self.geometry(self.default_main_window_position())

        self.main_frame = MainLayer(self)
        self.main_frame.pack(fill="both", expand=True)

    def default_main_window_position(self):
        x_position = self.winfo_screenwidth()
        y_position = self.winfo_screenheight() - APP_HEIGHT

        # return f"{APP_WIDTH}x{APP_HEIGHT}+{x_position}+{y_position}"
        return f"{APP_WIDTH}x{APP_HEIGHT}"

    def show_main_window(self):
        self.attributes("-fullscreen", False)
        self.attributes("-alpha", 1.0)
        self.configure(bg="SystemButtonFace")


class MainLayer(tk.Frame):
    """メイン操作画面。"""

    def __init__(self, root):
        super().__init__(master=root, bg="White")
        self.root = root
        self.pack(fill="both", expand=True)
        self.images = []
        self.create_widgets()

    def create_widgets(self):
        button_label = ["問題を撮影", "解答を撮影"]

        for i in range(len(button_label)):
            self.columnconfigure(i, weight=1, uniform="buttons")

        for column_number, btn in enumerate(button_label):
            self.create_screenshot_button(column_number, btn)

        self.create_image_area()

        self.create_add_question_button()

    def create_image_area(self):
        question_image_path = "./capture/20260616_question_001.png"
        answer_path = "./capture/20260616_answer_001.png"
        image_width_area = int(APP_WIDTH * 0.75)
        image_height_area = int(APP_HEIGHT * 0.75)

        for i, p in enumerate((question_image_path, answer_path)):
            image_area = tk.Canvas(
                self, width=image_width_area, height=image_height_area
            )

            # 画像を開く
            original_image = Image.open(p)
            w, h = original_image.width, original_image.height

            # アスペクト比を維持したまま表示領域に収まるスケールを計算
            fit_scale = min(image_width_area / w, image_height_area / h)

            # 画像をリサイズ
            resized_image = original_image.resize(
                (int(w * fit_scale), int(h * fit_scale))
            )
            photo_image = ImageTk.PhotoImage(resized_image)
            self.images.append(photo_image)

            # 中央配置の座標を計算
            x = (image_width_area - resized_image.width) // 2
            y = (image_height_area - resized_image.height) // 2

            image_area.create_image(
                x,
                y,
                anchor="nw",
                image=photo_image,
            )

            image_area.grid(row=1, column=i, sticky="nsew")

    def create_add_question_button(self):
        btn_add_question = tk.Button(self)
        btn_add_question["text"] = "Ankiに問題を追加"
        btn_add_question["command"] = self.on_click_add_question

        btn_add_question.grid(row=2, column=0, columnspan=2, sticky="nsew")

    def create_screenshot_button(self, column_number, text_name):
        btn_screenshot = tk.Button(self)
        btn_screenshot["text"] = text_name
        btn_screenshot["command"] = lambda: self.on_click_screenshot(column_number)

        btn_screenshot.grid(row=0, column=column_number, padx=1, sticky="we")

    def on_click_screenshot(self, state):
        self.show_screenshot(state)

    def show_screenshot(self, state):
        self.pack_forget()
        screen_layer = ScreenShotLayer(self.root, state)
        screen_layer.pack(fill="both", expand=True)

    def on_click_add_question(self):
        deck_name = "テスト"
        # 最新の問題・解答データのファイルパスを取得する
        question, answer = utils.get_latest_file(path)

        # Ankiのメディアフォルダへコピーする
        for file_path in (question, answer):
            file_data = utils.convert_file_to_base64(file_path)
            self.request_anki_connect(
                "storeMediaFile", filename=file_path.name, data=file_data
            )

        # 問題・解答をAnkiに追加する
        self.add_question(deck_name, question.name, answer.name)

    def request_anki_connect(self, action, **params):
        try:
            response = requests.post(
                "http://localhost:8765",
                json={"action": action, "params": params, "version": 6},
            )

            # 接続の確認
            response.raise_for_status()

            result = response.json()

            if result["error"] is not None:
                raise RuntimeError(result["error"])

            return result

        except requests.exceptions.ConnectionError as e:
            print(e)
            raise RuntimeError("Ankiが起動していません")

    def add_question(self, deck_name, front, back, tags=None):
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


class ScreenShotLayer(tk.Canvas):
    """画面上でドラッグ選択を受け付け、指定範囲を画像として保存するレイヤー。"""

    def __init__(self, root, state):
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
        self.bind("<ButtonRelease-1>", lambda e: self.on_release(e, state))

    def reset_coordinate(self):
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        # print(f"X座標: {self.start_x }、Y座標: {self.start_y }")

    def on_drag(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.create_screenshot_area()

    def on_release(self, event, state):
        self.end_x = event.x
        self.end_y = event.y
        # print(f"ドラッグX座標: {self.end_x }、ドラッグY座標: {self.end_y}")
        # print(self.root.winfo_screenwidth(), self.root.winfo_screenheight())

        self.screenshot(state)

        self.destroy()
        self.root.show_main_window()

        self.root.main_frame.pack(fill="both", expand=True)

    def create_screenshot_area(self):
        if self.rect_id:
            self.delete(self.rect_id)

        self.rect_id = self.create_rectangle(
            self.start_x,
            self.start_y,
            self.end_x,
            self.end_y,
            outline="Cyan",
            width=self.border_width,
            fill="white",
        )

    def screenshot(self, state):
        x1 = min(self.start_x, self.end_x) + self.border_width
        y1 = min(self.start_y, self.end_y) + self.border_width
        x2 = max(self.start_x, self.end_x) - self.border_width
        y2 = max(self.start_y, self.end_y) - self.border_width

        # スクリーンショットの保存ファイル名を生成する
        file_name = self.create_file_name(state)
        new_file_name = path / file_name

        # スクリーンショットレイヤーを一時的に非表示にする
        self.root.withdraw()

        try:
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img.save(new_file_name)
            messagebox.showinfo("完了", "保存しました")
        except OSError as e:
            messagebox.showerror(
                "撮影エラー", f"スクリーンショット取得に失敗しました\n{e}"
            )

        # スクリーンショットレイヤーを再表示する
        self.root.deiconify()

    def create_file_name(self, state):
        today = utils.get_today_ymd()

        if state == 0:
            today_files = sorted(Path(path).glob(f"*{today}*question*.png"))
        elif state == 1:
            today_files = sorted(Path(path).glob(f"*{today}*answer*.png"))

        kind = "question" if state == 0 else "answer"

        if not today_files:
            return f"{today}_{kind}_001.png"
        else:
            last_file = today_files[-1].stem
            last_number = int(last_file.split("_")[-1])

            return f"{today}_{kind}_{last_number + 1:03d}.png"


class PreviewImageLayer(tk.Canvas):
    def __init__(self, root=None, img=None):
        super().__init__(master=root, bg="White")
        self.root = root
        self.pack(fill="both", expand=True)

        self.img = img
        self.create_widgets()

    def create_widgets(self):
        if self.img is None:
            self.root.create_text(150, 100, text="No Image")
        else:
            self.create_img()

    def create_img(self):
        # 画像ファイルを開く
        self.photo_image = ImageTk.PhotoImage(file=self.img)

        # キャンバスのサイズを取得
        canvas_width = self.root.winfo_width()
        canvas_height = self.root.winfo_height()

        self.root.create_image(
            canvas_width / 2,
            canvas_height / 2,
            image=self.img,
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()
