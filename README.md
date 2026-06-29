# anki-snap-importer

画面の一部をキャプチャして、問題画像・解答画像を Anki にまとめて登録するためのデスクトップアプリです。

## 概要

学習中の問題と解答を `F5` で順番に切り取り、`Ctrl+S` で Anki ノートとして登録します。
登録時に OCR で画像内テキストを解析し、`config/config.json` のマッピングに基づいてタグを自動付与します。

## 主な機能

- 問題画像・解答画像を順番にキャプチャ
- 再撮影（問題/解答）
- AnkiConnect 経由で Anki にノート追加
- OCR + 形態素解析（Janome）によるタグ自動抽出
- 画像ファイルの連番管理
  - 形式: `YYYYMMDD_question_001.png` / `YYYYMMDD_answer_001.png`
  - `capture/` と `capture/completed/` をまたいで当日連番を継続

## 動作環境

- OS: Windows（前提）
- Python: 3.11 以上推奨
- Anki（デスクトップ版）
- AnkiConnect（Anki アドオン）
- Tesseract OCR（日本語+英語データ）

## インストール・セットアップ

1. リポジトリを取得

```powershell
git clone <this-repo-url>
cd anki-snap-importer
```

2. 仮想環境を作成して有効化

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. 依存パッケージをインストール

```powershell
pip install pillow requests python-dotenv pyocr janome pyinstaller
```

4. AnkiConnect を有効化した Anki をインストール

5. Tesseract OCR をインストールし、日本語・英語の言語データを有効化

6. `.env` をプロジェクトルートに作成

```env
ANKI_EXE_PATH=C:\Program Files\Anki\anki.exe
ANKI_CONNECT_URL=http://127.0.0.1:8765
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## 起動方法

```powershell
python main.py
```

起動時に `ANKI_EXE_PATH` で指定した Anki を自動起動します。

## 使い方

1. 問題を撮影
   - ボタン `問題を撮影(F5)` または `F5`
   - 左ドラッグで範囲選択
2. 解答を撮影
   - ボタン `解答を撮影(F5)` または `F5`
3. Anki へ登録
   - ボタン `Ankiに登録(Ctrl+s)` または `Ctrl+S`
4. 必要に応じて再撮影
   - `問題を再撮影` / `解答を再撮影`
5. キャプチャキャンセル
   - スクリーンショット画面で右クリック

登録完了後、画像は `capture/completed/` に移動します。

## Anki 登録仕様

- デッキ名: `応用情報技術者試験`
- ノートタイプ: `基本`
- フィールド
  - `表面`: 問題画像
  - `裏面`: 解答画像
- タグ
  - OCR + Janome で抽出した語を `config/config.json` と照合して追加

## 設定ファイル

- `config/config.json`
  - OCR で見つかった語を Anki タグ配列へ変換するマッピング
- `config/user_dict.csv`
  - Janome 用ユーザー辞書（`simpledic` 形式）

## ディレクトリ構成（主要部）

```text
.
|- main.py
|- src/
|  |- service/
|  |  |- capture_service.py
|  |  |- ocr_service.py
|  |- utils.py
|- config/
|  |- config.json
|  |- user_dict.csv
|- capture/
|  |- completed/
```

## 既知の注意点

- 画面キャプチャは GUI 操作前提です（ヘッドレス環境では動作しません）。
- `TESSERACT_PATH` や `ANKI_EXE_PATH` が誤っていると起動/登録に失敗します。
- Anki が起動していない、または AnkiConnect に接続できない場合は登録エラーになります。

## ビルド（任意）

PyInstaller を使って実行ファイル化する場合:

```powershell
pyinstaller anki-snap-importer.spec
```
