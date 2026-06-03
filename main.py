import tkinter as tk
from tkinter import *
from tkinter import ttk


def new_file():
    print("新しいファイルを作成しました")


def open_file():
    print("ファイルを開きました")


def copy_text():
    print("テキストをコピーしました。")


def paste_text():
    print("テキストを貼り付けました")


def show_context_menu(event):
    context_menu.post(event.x_root, event.y_root)


def show_info():
    messagebox.showinfo("情報", "これは情報メッセージボックスです！")


root = Tk()
root.geometry("600x300")

# メニューバーの構成
menubar = Menu(root)
file_menu = Menu(menubar, tearoff=0)
menubar.add_cascade(label="ファイル", menu=file_menu)
file_menu.add_command(label="新規作成", command=new_file)
file_menu.add_command(label="開く", command=open_file)
file_menu.add_separator()
file_menu.add_command(label="終了", command=root.quit)
root.config(menu=menubar)

# コンテキストメニューの構成
context_menu = Menu(root, tearoff=0)
context_menu.add_command(label="コピー", command=copy_text)
context_menu.add_command(label="貼り付け", command=paste_text)

# ボタンの配置
btn_info = tk.Button(root, text="情報メッセージ", command=show_info)
btn_info.pack(pady=5)

root.bind("<Button-3>", show_context_menu)

# 入力フィールドの配置
feet = StringVar()
feet_entry = ttk.Entry(root, width=7, textvariable=feet)
feet_entry.pack(pady=5)

root.mainloop()
