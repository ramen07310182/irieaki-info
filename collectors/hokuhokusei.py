import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://hokuhokusei-pr.com"
NEWS_URL = "https://hokuhokusei-pr.com/news/"

# プロジェクトのルートフォルダ
BASE_DIR = Path(__file__).resolve().parent.parent

# 保存先
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "news.json"


def get_news():
    """
    『北北西に曇と往け』公式サイトのNEWS一覧から
    日付・タイトル・URLを取得する。
    """

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        NEWS_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    news_list = []

    # NEWSページ内のすべてのリンクを確認
    for link in soup.find_all("a", href=True):

        text = link.get_text(" ", strip=True)

        if not text:
            continue

        # 「2026.04.28」のような日付を探す
        match = re.search(
            r"(\d{4})\.(\d{2})\.(\d{2})",
            text
        )

        if not match:
            continue

        # 日付
        date = (
            f"{match.group(1)}-"
            f"{match.group(2)}-"
            f"{match.group(3)}"
        )

        # 日付部分をタイトルから取り除く
        title = re.sub(
            r"^\d{4}\.\d{2}\.\d{2}\s*",
            "",
            text
        ).strip()

        if not title:
            continue

        # 相対URLを絶対URLに変換
        url = urljoin(
            BASE_URL,
            link["href"]
        )

        news_list.append({
            "date": date,
            "title": title,
            "source": "北北西に曇と往け公式",
            "category": "公式ニュース",
            "url": url
        })

    # URLを使って重複排除
    unique_news = []
    seen_urls = set()

    for item in news_list:

        if item["url"] in seen_urls:
            continue

        seen_urls.add(item["url"])
        unique_news.append(item)

    return unique_news


def load_saved_news():
    """
    既に保存されているnews.jsonを読み込む。
    ファイルが存在しない場合は空のリストを返す。
    """

    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except (json.JSONDecodeError, OSError):
        return []


def save_news(new_news):
    """
    新しく取得したニュースをnews.jsonに追加する。

    同じURLのニュースは重複して保存しない。
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    saved_news = load_saved_news()

    # 既存URLを取得
    existing_urls = {
        item.get("url")
        for item in saved_news
        if item.get("url")
    }

    added_count = 0

    for item in new_news:

        if item["url"] in existing_urls:
            continue

        saved_news.append(item)
        existing_urls.add(item["url"])
        added_count += 1

    # 日付の新しい順に並べる
    saved_news.sort(
        key=lambda x: x.get("date", ""),
        reverse=True
    )

    # JSONとして保存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            saved_news,
            f,
            ensure_ascii=False,
            indent=2
        )

    return added_count, len(saved_news)


if __name__ == "__main__":

    print("『北北西に曇と往け』公式サイトを確認しています...")
    print()

    try:

        news = get_news()

        if not news:
            print("ニュースを取得できませんでした。")

        else:

            print(
                f"{len(news)}件のニュースを取得しました。"
            )

            print()

            added_count, total_count = save_news(news)

            print(
                f"新しく追加したニュース: {added_count}件"
            )

            print(
                f"保存されているニュース: {total_count}件"
            )

            print()

            print(f"保存先: {DATA_FILE}")

    except requests.RequestException as e:

        print("サイトへのアクセスに失敗しました。")
        print(f"エラー: {e}")

    except Exception as e:

        print("データの保存中にエラーが発生しました。")
        print(f"エラー: {e}")