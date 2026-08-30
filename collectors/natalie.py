import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://natalie.mu"

NEWS_URL = (
    "https://natalie.mu/comic/news/list/artist_id/2343"
)

# プロジェクトのルートフォルダ
BASE_DIR = Path(__file__).resolve().parent.parent

# 保存先
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "news.json"


def get_news():
    """
    コミックナタリーの入江亜季関連ニュースから
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

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    news_list = []

    # ページ内のリンクを確認
    for link in soup.find_all("a", href=True):

        text = link.get_text(" ", strip=True)

        if not text:
            continue

        href = link["href"]

        # コミックナタリーの記事URLだけを対象にする
        if "/comic/news/" not in href:
            continue

        # 日付を探す
        match = re.search(
            r"(\d{4})[./年](\d{1,2})[./月](\d{1,2})",
            text
        )

        if not match:
            continue

        date = (
            f"{match.group(1)}-"
            f"{int(match.group(2)):02d}-"
            f"{int(match.group(3)):02d}"
        )

        # タイトルから日付表記を削除
        title = re.sub(
            r"^\s*[\[\【]?\s*"
            r"\d{4}[./年]\d{1,2}[./月]\d{1,2}日?"
            r"\s*[\]\】]?\s*",
            "",
            text
        ).strip()

        # 「2026年5月4日～」などがタイトル先頭に残った場合
        title = re.sub(
            r"^\s*[\[\【]?\s*"
            r"\d{4}年\d{1,2}月\d{1,2}日"
            r"\s*",
            "",
            title
        ).strip()

        if not title:
            continue

        # 相対URLを絶対URLへ変換
        url = urljoin(
            BASE_URL,
            href
        )

        news_list.append({
            "date": date,
            "title": title,
            "source": "コミックナタリー",
            "category": "ニュース",
            "url": url
        })

    # URLで重複排除
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
    既存のnews.jsonを読み込む。
    """

    if not DATA_FILE.exists():
        return []

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except (json.JSONDecodeError, OSError):

        return []


def save_news(new_news):
    """
    新しく取得したニュースを
    既存のnews.jsonに追加する。

    既存データは削除しない。
    同じURLのニュースは重複登録しない。
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    saved_news = load_saved_news()

    # 既に保存されているURL
    existing_urls = {
        item.get("url")
        for item in saved_news
        if item.get("url")
    }

    added_count = 0

    for item in new_news:

        # 既に登録されている場合はスキップ
        if item["url"] in existing_urls:
            continue

        saved_news.append(item)

        existing_urls.add(
            item["url"]
        )

        added_count += 1

    # 日付の新しい順
    saved_news.sort(
        key=lambda x: x.get("date", ""),
        reverse=True
    )

    # 保存
    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            saved_news,
            f,
            ensure_ascii=False,
            indent=2
        )

    return added_count, len(saved_news)


if __name__ == "__main__":

    print(
        "コミックナタリーを確認しています..."
    )

    print()

    try:

        # ニュース取得
        news = get_news()

        if not news:

            print(
                "ニュースを取得できませんでした。"
            )

        else:

            print(
                f"{len(news)}件のニュースを取得しました。"
            )

            print()

            # news.jsonへ保存
            added_count, total_count = save_news(
                news
            )

            print(
                f"新しく追加したニュース: "
                f"{added_count}件"
            )

            print(
                f"保存されているニュース: "
                f"{total_count}件"
            )

            print()

            print(
                f"保存先: {DATA_FILE}"
            )

    except requests.RequestException as e:

        print(
            "サイトへのアクセスに失敗しました。"
        )

        print(f"エラー: {e}")

    except Exception as e:

        print(
            "データの保存中にエラーが発生しました。"
        )

        print(f"エラー: {e}")