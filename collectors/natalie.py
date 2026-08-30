import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

BASE_URL = "https://natalie.mu"

NEWS_URL = (
    "https://natalie.mu/comic/news/list/artist_id/2343"
)

# プロジェクトのルートフォルダ
BASE_DIR = Path(__file__).resolve().parent.parent

# 保存先
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "news.json"

# 通常アクセス間隔
REQUEST_INTERVAL = 3

# 最大再試行回数
MAX_RETRIES = 3

# 再試行待機時間
RETRY_WAIT_TIMES = [
    10,
    30,
    60,
]


# ============================================================
# HTTPヘッダー
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),

    "Accept-Language": (
        "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
    ),

    "Accept-Encoding": (
        "gzip, deflate, br"
    ),

    "Connection": "keep-alive",

    "Upgrade-Insecure-Requests": "1",

    "Sec-Fetch-Dest": "document",

    "Sec-Fetch-Mode": "navigate",

    "Sec-Fetch-Site": "none",

    "Sec-Fetch-User": "?1",
}


# ============================================================
# Session
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ============================================================
# URLアクセス
# ============================================================

def request_news_page():

    for attempt in range(MAX_RETRIES):

        try:

            print(
                f"コミックナタリーへアクセス中..."
                f"（試行 {attempt + 1}/{MAX_RETRIES}）"
            )

            response = session.get(
                NEWS_URL,
                timeout=30,
                allow_redirects=True,
            )

            print(
                f"HTTPステータス: "
                f"{response.status_code}"
            )

            # ------------------------------------------------
            # 成功
            # ------------------------------------------------

            if response.status_code == 200:

                time.sleep(
                    REQUEST_INTERVAL
                )

                return response

            # ------------------------------------------------
            # 405
            # ------------------------------------------------

            if response.status_code == 405:

                print(
                    "405 Method Not Allowed"
                )

                if attempt < MAX_RETRIES - 1:

                    wait_time = RETRY_WAIT_TIMES[
                        attempt
                    ]

                    print(
                        f"{wait_time}秒待って再試行します..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                print(
                    "405エラーのため取得を中止します。"
                )

                return None

            # ------------------------------------------------
            # 403
            # ------------------------------------------------

            if response.status_code == 403:

                print(
                    "403 Forbidden"
                )

                if attempt < MAX_RETRIES - 1:

                    wait_time = RETRY_WAIT_TIMES[
                        attempt
                    ]

                    print(
                        f"{wait_time}秒待って再試行します..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                print(
                    "403エラーのため取得を中止します。"
                )

                return None

            # ------------------------------------------------
            # 429
            # ------------------------------------------------

            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                if retry_after:

                    try:

                        wait_time = int(
                            retry_after
                        )

                    except ValueError:

                        wait_time = RETRY_WAIT_TIMES[
                            attempt
                        ]

                else:

                    wait_time = RETRY_WAIT_TIMES[
                        attempt
                    ]

                print(
                    "429 Too Many Requests"
                )

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                if attempt < MAX_RETRIES - 1:

                    time.sleep(
                        wait_time
                    )

                    continue

                return None

            # ------------------------------------------------
            # その他
            # ------------------------------------------------

            print(
                f"HTTPエラー: "
                f"{response.status_code}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = RETRY_WAIT_TIMES[
                    attempt
                ]

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

                continue

            return None

        except requests.RequestException as e:

            print(
                f"通信エラー: {e}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = RETRY_WAIT_TIMES[
                    attempt
                ]

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

                continue

            return None

    return None


# ============================================================
# ニュース取得
# ============================================================

def get_news():
    """
    コミックナタリーの入江亜季関連ニュースから
    日付・タイトル・URLを取得する。
    """

    response = request_news_page()

    if response is None:

        raise RuntimeError(
            "コミックナタリーへのアクセスに失敗しました。"
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    news_list = []

    # ========================================================
    # ページ内のリンクを確認
    # ========================================================

    for link in soup.find_all(
        "a",
        href=True
    ):

        text = link.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        href = link["href"]

        # ----------------------------------------------------
        # コミックナタリーの記事URLだけを対象
        # ----------------------------------------------------

        if "/comic/news/" not in href:
            continue

        # ----------------------------------------------------
        # 日付を探す
        # ----------------------------------------------------

        match = re.search(
            r"(\d{4})[./年]"
            r"(\d{1,2})[./月]"
            r"(\d{1,2})",
            text
        )

        if not match:
            continue

        date = (
            f"{match.group(1)}-"
            f"{int(match.group(2)):02d}-"
            f"{int(match.group(3)):02d}"
        )

        # ----------------------------------------------------
        # タイトルから日付表記を削除
        # ----------------------------------------------------

        title = re.sub(
            r"^\s*[\[\【]?\s*"
            r"\d{4}[./年]\d{1,2}[./月]\d{1,2}日?"
            r"\s*[\]\】]?\s*",
            "",
            text
        ).strip()

        # ----------------------------------------------------
        # 「2026年5月4日～」などが残った場合
        # ----------------------------------------------------

        title = re.sub(
            r"^\s*[\[\【]?\s*"
            r"\d{4}年\d{1,2}月\d{1,2}日"
            r"\s*",
            "",
            title
        ).strip()

        if not title:
            continue

        # ----------------------------------------------------
        # 相対URLを絶対URLへ
        # ----------------------------------------------------

        url = urljoin(
            BASE_URL,
            href
        )

        news_list.append(
            {
                "date": date,
                "title": title,
                "source": "コミックナタリー",
                "category": "ニュース",
                "url": url,
            }
        )

    # ========================================================
    # URLで重複排除
    # ========================================================

    unique_news = []

    seen_urls = set()

    for item in news_list:

        if item["url"] in seen_urls:
            continue

        seen_urls.add(
            item["url"]
        )

        unique_news.append(
            item
        )

    return unique_news


# ============================================================
# news.json読み込み
# ============================================================

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

        if isinstance(
            data,
            list
        ):

            return data

        return []

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


# ============================================================
# news.json保存
# ============================================================

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

    # --------------------------------------------------------
    # 既存URL
    # --------------------------------------------------------

    existing_urls = {
        item.get("url")
        for item in saved_news
        if item.get("url")
    }

    added_count = 0

    # --------------------------------------------------------
    # 新しいニュースを追加
    # --------------------------------------------------------

    for item in new_news:

        if item["url"] in existing_urls:

            continue

        saved_news.append(
            item
        )

        existing_urls.add(
            item["url"]
        )

        added_count += 1

    # --------------------------------------------------------
    # 日付の新しい順
    # --------------------------------------------------------

    saved_news.sort(
        key=lambda x: x.get(
            "date",
            ""
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # 保存
    # --------------------------------------------------------

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

    return (
        added_count,
        len(saved_news)
    )


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print(
        "コミックナタリーを確認しています..."
    )

    print()

    try:

        # ====================================================
        # ニュース取得
        # ====================================================

        news = get_news()

        if not news:

            print(
                "ニュースを取得できませんでした。"
            )

            # GitHub Actionsでも失敗扱いにする
            sys.exit(1)

        print(
            f"{len(news)}件のニュースを取得しました。"
        )

        print()

        # ====================================================
        # news.jsonへ保存
        # ====================================================

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

        print()

        print(
            "コミックナタリーの処理が完了しました。"
        )

    except requests.RequestException as e:

        print(
            "サイトへのアクセスに失敗しました。"
        )

        print(
            f"エラー: {e}"
        )

        # GitHub Actionsを失敗扱いにする
        sys.exit(1)

    except Exception as e:

        print(
            "データの取得・保存中に"
            "エラーが発生しました。"
        )

        print(
            f"エラー: {e}"
        )

        # GitHub Actionsを失敗扱いにする
        sys.exit(1)