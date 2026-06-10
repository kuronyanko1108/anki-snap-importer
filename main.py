import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab
from pathlib import Path
import ctypes
import platform

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

path = Path.cwd() / "capture"
APP_WIDTH = 400
APP_HEIGHT = 200


class App(tk.Tk):
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
    def __init__(self, root):
        super().__init__(master=root, bg="White")
        self.root = root
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        self.create_screenshot_button()

    def create_screenshot_button(self):
        btn_screenshot = tk.Button(self)
        btn_screenshot["text"] = "撮影"
        btn_screenshot["command"] = self.on_click_screenshot
        btn_screenshot.pack()

    def on_click_screenshot(self):
        self.show_screenshot()

    def show_screenshot(self):
        self.pack_forget()
        screen_layer = ScreenShotLayer(self.root)
        screen_layer.pack(fill="both", expand=True)


class ScreenShotLayer(tk.Canvas):
    def __init__(self, root):
        super().__init__(master=root)
        self.root = root
        self.rect_id = None
        self.border_width = 10

        # ウィンドウのフルスクリーン・半透明化
        self.root.configure(bg="Black")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.5)

        # イベントのバインド
        self.root.bind("<ButtonPress-1>", self.on_press)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        print(f"X座標: {self.start_x }、Y座標: {self.start_y }")

    def on_drag(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.create_screenshot_area()

    def on_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        print(f"ドラッグX座標: {self.end_x }、ドラッグY座標: {self.end_y}")
        print(self.root.winfo_screenwidth(), self.root.winfo_screenheight())

        self.screenshot()
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

    def screenshot(self):
        x1 = min(self.start_x, self.end_x) + self.border_width
        y1 = min(self.start_y, self.end_y) + self.border_width
        x2 = max(self.start_x, self.end_x) - self.border_width
        y2 = max(self.start_y, self.end_y) - self.border_width

        file_name = path / "screenshot.png"

        try:
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img.save(file_name)
            messagebox.showinfo("完了", "screenshot.png を保存しました")
        except OSError as e:
            messagebox.showerror(
                "撮影エラー", f"スクリーンショット取得に失敗しました\n{e}"
            )


if __name__ == "__main__":
    app = App()
    app.mainloop()
