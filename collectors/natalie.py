import json
import re
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


# ============================================================
# HTTP設定
# ============================================================

# GitHub Actionsからのアクセスを想定して、
# ブラウザに近いヘッダーを使用する。
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,"
        "*/*;q=0.8"
    ),
    "Accept-Language": (
        "ja,en-US;q=0.9,en;q=0.8"
    ),
    "Accept-Encoding": (
        "gzip, deflate"
    ),
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# 通常のリトライ回数
MAX_RETRIES = 3

# 通信エラー時の待機時間
REQUEST_ERROR_WAIT = [
    10,
    30,
    60
]

# 405の場合
# 同じアクセスを何度も繰り返しても改善しない可能性が
# 高いため、短時間で打ち切る。
METHOD_NOT_ALLOWED_WAIT = [
    10,
    30
]


# ============================================================
# Session
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ============================================================
# ニュース取得
# ============================================================

def get_news():
    """
    コミックナタリーの入江亜季関連ニュースから
    日付・タイトル・URLを取得する。

    GitHub Actionsから405などが発生した場合は、
    その回の取得を中止して空リストを返す。
    """

    print(
        "コミックナタリーへアクセスしています..."
    )

    response = None

    for attempt in range(
        MAX_RETRIES
    ):

        print(
            f"コミックナタリーへアクセス中..."
            f"（試行 {attempt + 1}/{MAX_RETRIES}）"
        )

        try:

            response = session.get(
                NEWS_URL,
                timeout=30,
                allow_redirects=True
            )

            print(
                f"HTTPステータス: "
                f"{response.status_code}"
            )

            # ------------------------------------------------
            # 成功
            # ------------------------------------------------

            if response.status_code == 200:

                break

            # ------------------------------------------------
            # 405
            # ------------------------------------------------

            if response.status_code == 405:

                print(
                    "405 Method Not Allowed"
                )

                # Allowヘッダーがあれば表示
                allow_methods = response.headers.get(
                    "Allow"
                )

                if allow_methods:

                    print(
                        f"許可されているHTTPメソッド: "
                        f"{allow_methods}"
                    )

                if attempt < len(
                    METHOD_NOT_ALLOWED_WAIT
                ):

                    wait_time = (
                        METHOD_NOT_ALLOWED_WAIT[
                            attempt
                        ]
                    )

                    print(
                        f"{wait_time}秒待って再試行します..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                print(
                    "405エラーのため"
                    "今回の取得を中止します。"
                )

                return []

            # ------------------------------------------------
            # 403
            # ------------------------------------------------

            if response.status_code == 403:

                print(
                    "403 Forbidden"
                )

                if attempt < MAX_RETRIES - 1:

                    wait_time = (
                        REQUEST_ERROR_WAIT[
                            attempt
                        ]
                    )

                    print(
                        f"{wait_time}秒待って再試行します..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                print(
                    "403エラーのため"
                    "今回の取得を中止します。"
                )

                return []

            # ------------------------------------------------
            # 429
            # ------------------------------------------------

            if response.status_code == 429:

                print(
                    "429 Too Many Requests"
                )

                retry_after = response.headers.get(
                    "Retry-After"
                )

                if retry_after:

                    try:

                        wait_time = int(
                            retry_after
                        )

                    except ValueError:

                        wait_time = 60

                else:

                    wait_time = 60

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

                continue

            # ------------------------------------------------
            # その他のHTTPエラー
            # ------------------------------------------------

            print(
                f"HTTPエラー: "
                f"{response.status_code}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = (
                    REQUEST_ERROR_WAIT[
                        attempt
                    ]
                )

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

                continue

            print(
                "今回の取得を中止します。"
            )

            return []

        except requests.RequestException as e:

            print(
                f"通信エラー: {e}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = (
                    REQUEST_ERROR_WAIT[
                        attempt
                    ]
                )

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

                continue

            print(
                "通信エラーのため"
                "今回の取得を中止します。"
            )

            return []

    # ========================================================
    # 200以外の場合
    # ========================================================

    if response is None:

        return []

    if response.status_code != 200:

        print(
            "ニュースページを取得できませんでした。"
        )

        return []

    # ========================================================
    # HTML解析
    # ========================================================

    print(
        "ニュースページを取得しました。"
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
        # URLを絶対URLへ
        # ----------------------------------------------------

        url = urljoin(
            BASE_URL,
            href
        )

        # ----------------------------------------------------
        # 日付を探す
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # タイトル
        # ----------------------------------------------------

        title = text

        # 先頭の日付を削除
        title = re.sub(
            r"^\s*[\[\【]?\s*"
            r"\d{4}[./年]\d{1,2}[./月]\d{1,2}日?"
            r"\s*[\]\】]?\s*",
            "",
            title
        ).strip()

        # 「2026年5月4日～」などがタイトル先頭に
        # 残った場合
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
        # データ作成
        # ----------------------------------------------------

        news_list.append({
            "date": date,
            "title": title,
            "source": "コミックナタリー",
            "category": "ニュース",
            "url": url
        })

    # ========================================================
    # URLで重複排除
    # ========================================================

    unique_news = []

    seen_urls = set()

    for item in news_list:

        url = item["url"]

        if url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        unique_news.append(
            item
        )

    print(
        f"{len(unique_news)}件のニュースを取得しました。"
    )

    return unique_news


# ============================================================
# 既存news.json読み込み
# ============================================================

def load_saved_news():
    """
    既存のnews.jsonを読み込む。
    """

    if not DATA_FILE.exists():

        print(
            "news.jsonがまだ存在しません。"
        )

        return []

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(
                f
            )

        if isinstance(
            data,
            list
        ):

            print(
                f"既存ニュース: "
                f"{len(data)}件"
            )

            return data

        print(
            "news.jsonの形式が不正です。"
        )

        return []

    except (
        json.JSONDecodeError,
        OSError
    ) as e:

        print(
            f"news.jsonの読み込みに失敗しました: "
            f"{e}"
        )

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
    # 新規データ追加
    # --------------------------------------------------------

    for item in new_news:

        url = item.get(
            "url"
        )

        if not url:
            continue

        # 既に存在
        if url in existing_urls:

            continue

        saved_news.append(
            item
        )

        existing_urls.add(
            url
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

        # ----------------------------------------------------
        # 取得できなかった場合
        # ----------------------------------------------------

        if not news:

            print()

            print(
                "コミックナタリーから"
                "ニュースを取得できませんでした。"
            )

            print(
                "今回はコミックナタリーを"
                "スキップします。"
            )

            print(
                "既存のnews.jsonは変更しません。"
            )

            # ------------------------------------------------
            # 重要
            #
            # GitHub Actions全体を失敗させない。
            # ------------------------------------------------

            exit(0)

        # ====================================================
        # 取得成功
        # ====================================================

        print()

        # ====================================================
        # news.jsonへ保存
        # ====================================================

        added_count, total_count = save_news(
            news
        )

        print()

        print(
            "=" * 60
        )

        print(
            "コミックナタリー取得結果"
        )

        print(
            "=" * 60
        )

        print(
            f"今回取得したニュース: "
            f"{len(news)}件"
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

        print(
            "=" * 60
        )

        # ====================================================
        # 今回取得したニュースを表示
        # ====================================================

        print()

        print(
            "【今回取得したニュース】"
        )

        print()

        for item in news:

            print(
                f"日付: {item['date']}"
            )

            print(
                f"タイトル: {item['title']}"
            )

            print(
                f"URL: {item['url']}"
            )

            print(
                "-" * 60
            )

    # ========================================================
    # 通信エラー
    # ========================================================

    except requests.RequestException as e:

        print()

        print(
            "コミックナタリーへの"
            "アクセスに失敗しました。"
        )

        print(
            f"エラー: {e}"
        )

        print(
            "今回はコミックナタリーをスキップします。"
        )

        # GitHub Actionsを失敗させない
        exit(0)

    # ========================================================
    # その他のエラー
    # ========================================================

    except Exception as e:

        print()

        print(
            "コミックナタリーの"
            "取得処理でエラーが発生しました。"
        )

        print(
            f"エラー: {e}"
        )

        print(
            "今回はコミックナタリーをスキップします。"
        )

        # GitHub Actionsを失敗させない
        exit(0)