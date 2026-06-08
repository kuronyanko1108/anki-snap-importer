import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab


class application(tk.Frame):
    def __init__(self, root):
        super().__init__(
            master=root, bg="White", width=1000, height=400, border=2, relief="raised"
        )
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
        try:
            # WSLg/Wayland では xdisplay="" を指定すると外部取得にフォールバックしやすい
            img = ImageGrab.grab(xdisplay="")
            img.save("screenshot.png")
            messagebox.showinfo("完了", "screenshot.png を保存しました")
        except OSError as e:
            messagebox.showerror(
                "撮影エラー", f"スクリーンショット取得に失敗しました\n{e}"
            )


root = tk.Tk()
root.title("anki_snap_importer")

APP_WIDTH = 300
APP_HEIGHT = 200
# X_POSITION = root.winfo_screenwidth() - APP_WIDTH
X_POSITION = 1600
# Y_POSITION = root.winfo_screenheight() - APP_HEIGHT
Y_POSITION = 780
PLUS = "+"
CRROcE = "x"
APP_POSITION = (
    str(APP_WIDTH)
    + CRROcE
    + str(APP_HEIGHT)
    + PLUS
    + str(X_POSITION)
    + PLUS
    + str(Y_POSITION)
)

root.geometry(APP_POSITION)
app = application(root=root)
app.mainloop()
