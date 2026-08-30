import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.bookcellar.jp"

PUBLISHER_URL = (
    "https://www.bookcellar.jp/publishertop/list/1481"
)

TARGET_AUTHOR = "入江 亜季"

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "news.json"


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def normalize_text(text):
    """
    空白を整理する。
    """

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def get_product_links():
    """
    雪割草の出版社ページから
    商品詳細ページのURLを取得する。
    """

    response = requests.get(
        PUBLISHER_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    product_links = []

    seen_urls = set()

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/product/detail/" not in href:
            continue

        url = urljoin(
            BASE_URL,
            href
        )

        if url in seen_urls:
            continue

        seen_urls.add(url)

        product_links.append(url)

    return product_links


def get_book_detail(url):
    """
    商品詳細ページを開いて、
    著者が入江亜季か確認する。

    入江亜季でなければNoneを返す。
    """

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    text = normalize_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # ==========================================
    # 著者を確認
    # ==========================================

    author_match = re.search(
        r"著者\s+([^ ]+ [^ ]+)",
        text
    )

    author = ""

    if author_match:

        author = normalize_text(
            author_match.group(1)
        )

    # 商品詳細ページに
    # 「入江 亜季」が明確に存在するか確認
    if TARGET_AUTHOR not in text:

        return None

    # 「著者」付近をより厳密に確認
    author_area = ""

    author_index = text.find("著者")

    if author_index >= 0:

        author_area = text[
            author_index:
            author_index + 50
        ]

    if TARGET_AUTHOR not in author_area:

        return None

    # ==========================================
    # タイトル
    # ==========================================

    title = ""

    h1 = soup.find("h1")

    if h1:

        title = normalize_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

    if not title:

        # h1が取れない場合の予備
        title_match = re.search(
            r"^(.+?)\s+\(",
            text
        )

        if title_match:

            title = normalize_text(
                title_match.group(1)
            )

    # ==========================================
    # 発売日
    # ==========================================

    date_match = re.search(
        r"(\d{4})/(\d{2})/(\d{2})発売",
        text
    )

    if not date_match:

        return None

    date = (
        f"{date_match.group(1)}-"
        f"{date_match.group(2)}-"
        f"{date_match.group(3)}"
    )

    # ==========================================
    # ISBN
    # ==========================================

    isbn_match = re.search(
        r"ISBN\s+"
        r"(97[89]-[\d-]+)",
        text
    )

    isbn = ""

    if isbn_match:

        isbn = (
            isbn_match
            .group(1)
            .replace(
                "-",
                ""
            )
        )

    # ==========================================
    # 価格
    # ==========================================

    price_match = re.search(
        r"¥\s*([\d,]+)",
        text
    )

    price = ""

    if price_match:

        price = (
            price_match
            .group(1)
            .replace(
                ",",
                ""
            )
        )

    return {
        "date": date,
        "title": title,
        "source": "雪割草",
        "category": "出版情報",
        "author": TARGET_AUTHOR,
        "url": url,
        "isbn": isbn,
        "price": price
    }


def get_books():
    """
    雪割草の商品一覧から商品を取得し、
    商品詳細ページで著者を確認する。
    """

    product_links = get_product_links()

    books = []

    print(
        f"{len(product_links)}件の商品を確認します。"
    )

    print()

    for url in product_links:

        print(
            f"確認中: {url}"
        )

        try:

            book = get_book_detail(
                url
            )

            if book is None:

                print(
                    "  → 入江亜季ではないため除外"
                )

                continue

            books.append(book)

            print(
                f"  → 入江亜季: {book['title']}"
            )

        except Exception as e:

            print(
                f"  → エラー: {e}"
            )

    return books


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

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


def save_books(new_books):
    """
    取得した出版情報を
    既存のnews.jsonに追加する。
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    saved_news = load_saved_news()

    existing_urls = {
        item.get("url")
        for item in saved_news
        if item.get("url")
    }

    added_count = 0

    for item in new_books:

        if item["url"] in existing_urls:

            continue

        saved_news.append(
            item
        )

        existing_urls.add(
            item["url"]
        )

        added_count += 1

    # 日付の新しい順
    saved_news.sort(
        key=lambda x: x.get(
            "date",
            ""
        ),
        reverse=True
    )

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


if __name__ == "__main__":

    print(
        "雪割草を確認しています..."
    )

    print(
        f"対象著者: {TARGET_AUTHOR}"
    )

    print()

    try:

        books = get_books()

        print()

        if not books:

            print(
                "入江亜季さんの出版情報は"
                "見つかりませんでした。"
            )

        else:

            print(
                f"入江亜季さんの出版情報:"
                f"{len(books)}件"
            )

            print()

            for book in books:

                print(
                    f"発売日: {book['date']}"
                )

                print(
                    f"タイトル: {book['title']}"
                )

                print(
                    f"著者: {book['author']}"
                )

                print(
                    f"ISBN: {book['isbn']}"
                )

                print(
                    f"価格: {book['price']}円"
                )

                print(
                    f"URL: {book['url']}"
                )

                print(
                    "-" * 60
                )

            print()

            added_count, total_count = save_books(
                books
            )

            print(
                f"新しく追加した出版情報: "
                f"{added_count}件"
            )

            print(
                f"news.jsonの全データ: "
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

        print(
            f"エラー: {e}"
        )

    except Exception as e:

        print(
            "データの取得・保存中に"
            "エラーが発生しました。"
        )

        print(
            f"エラー: {e}"
        )