import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

BASE_URL = "https://www.bookcellar.jp"

PUBLISHER_URL = (
    "https://www.bookcellar.jp/publishertop/list/1481"
)

TARGET_AUTHOR = "入江 亜季"

# プロジェクトのルートフォルダ
BASE_DIR = Path(__file__).resolve().parent.parent

# 保存先
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "news.json"


# ============================================================
# HTTP設定
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


# ============================================================
# 文字列整理
# ============================================================

def normalize_text(text):
    """
    空白を整理する。
    """

    if text is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ============================================================
# 著者名整理
# ============================================================

def normalize_author_name(name):
    """
    著者名から空白を除去する。
    """

    name = normalize_text(name)

    return (
        name
        .replace(" ", "")
        .replace("　", "")
    )


# ============================================================
# 商品一覧取得
# ============================================================

def get_product_links():
    """
    雪割草の出版社ページから
    商品詳細ページのURLを取得する。
    """

    print(
        "出版社の商品一覧へアクセスしています..."
    )

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

        url = url.rstrip("/")

        if url in seen_urls:
            continue

        seen_urls.add(url)

        product_links.append(url)

    return product_links


# ============================================================
# 著者取得
# ============================================================

def get_authors(soup):
    """
    商品ページから著者を取得する。

    「著者」が複数存在する場合も
    それぞれ取得する。
    """

    authors = []

    text = normalize_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # --------------------------------------------------------
    # 「著者」周辺を確認
    # --------------------------------------------------------

    matches = re.findall(
        r"著者\s+(.{1,80}?)(?=\s+(?:出版社|発売日|ISBN|価格|内容紹介|商品情報|商品詳細)|$)",
        text
    )

    for match in matches:

        author_text = normalize_text(
            match
        )

        if not author_text:
            continue

        # 「入江 亜季」などを分割して扱う
        # ただし余計な項目が入った場合は除去
        author_text = re.split(
            r"\s+(?:出版社|発売日|ISBN|価格|内容紹介|商品情報|商品詳細)",
            author_text
        )[0]

        author_text = normalize_text(
            author_text
        )

        if author_text:

            if author_text not in authors:

                authors.append(
                    author_text
                )

    # --------------------------------------------------------
    # ページ内の「入江 亜季」を補助的に確認
    # --------------------------------------------------------

    if not authors:

        target_normalized = normalize_author_name(
            TARGET_AUTHOR
        )

        if target_normalized in normalize_author_name(text):

            authors.append(
                TARGET_AUTHOR
            )

    return authors


# ============================================================
# 著者判定
# ============================================================

def is_target_author_only(soup):
    """
    著者が入江亜季1人だけの場合のみTrue。

    他の著者が存在する場合は除外する。
    """

    authors = get_authors(
        soup
    )

    print(
        f"  → 著者数: {len(authors)}"
    )

    if authors:

        print(
            "  → 著者: "
            + ", ".join(authors)
        )

    # 著者を取得できない
    if not authors:

        print(
            "  → 著者を確認できないため除外"
        )

        return False

    # 複数著者
    if len(authors) > 1:

        print(
            "  → 複数著者のため除外"
        )

        return False

    # 入江亜季以外
    if normalize_author_name(
        authors[0]
    ) != normalize_author_name(
        TARGET_AUTHOR
    ):

        print(
            "  → 著者が入江亜季ではないため除外"
        )

        return False

    print(
        "  → 著者が入江亜季1人なので採用"
    )

    return True


# ============================================================
# タイトル候補の整理
# ============================================================

def clean_title(title):
    """
    タイトル候補から不要な文字を除去する。
    """

    title = normalize_text(
        title
    )

    if not title:
        return ""

    # 絶対にタイトルとして使用しない文字
    invalid_titles = {
        "内容紹介",
        "商品情報",
        "商品詳細",
        "詳細",
        "著者",
        "書籍情報",
        "本の内容",
    }

    if title in invalid_titles:

        return ""

    # 「｜BookCellar」などを除去
    title = re.split(
        r"\s*[｜|]\s*",
        title
    )[0]

    # BookCellar関連の表記を除去
    title = re.sub(
        r"\s*[-–—]\s*BookCellar.*$",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\s*BookCellar.*$",
        "",
        title,
        flags=re.IGNORECASE
    )

    # 「本の通販」「書籍」などを除去
    title = re.sub(
        r"\s*[-–—]\s*本の通販.*$",
        "",
        title
    )

    title = normalize_text(
        title
    )

    if title in invalid_titles:

        return ""

    return title


# ============================================================
# 商品タイトル取得
# ============================================================

def get_product_title(soup):
    """
    BookCellarの商品ページから
    実際の書籍タイトルを取得する。

    h1だけに頼らず、

    1. OGP
    2. titleタグ
    3. 商品情報付近
    4. h1

    の順番で候補を確認する。
    """

    candidates = []

    # ========================================================
    # 1. OGP title
    # ========================================================

    og_title = soup.find(
        "meta",
        property="og:title"
    )

    if og_title:

        value = og_title.get(
            "content",
            ""
        )

        value = clean_title(
            value
        )

        if value:

            candidates.append(
                value
            )

    # ========================================================
    # 2. meta name="title"
    # ========================================================

    meta_title = soup.find(
        "meta",
        attrs={
            "name": "title"
        }
    )

    if meta_title:

        value = meta_title.get(
            "content",
            ""
        )

        value = clean_title(
            value
        )

        if value:

            candidates.append(
                value
            )

    # ========================================================
    # 3. titleタグ
    # ========================================================

    title_tag = soup.find(
        "title"
    )

    if title_tag:

        value = normalize_text(
            title_tag.get_text(
                " ",
                strip=True
            )
        )

        value = clean_title(
            value
        )

        if value:

            candidates.append(
                value
            )

    # ========================================================
    # 4. 商品名・書名などのラベルを探す
    # ========================================================

    labels = soup.find_all(
        string=re.compile(
            r"^(商品名|書名|タイトル|書籍名)$"
        )
    )

    for label in labels:

        parent = label.parent

        if parent is None:
            continue

        # ----------------------------------------------------
        # 親要素内
        # ----------------------------------------------------

        parent_text = normalize_text(
            parent.get_text(
                " ",
                strip=True
            )
        )

        # ラベルそのものを除去
        parent_text = re.sub(
            r"^(商品名|書名|タイトル|書籍名)\s*[:：]?\s*",
            "",
            parent_text
        )

        parent_text = clean_title(
            parent_text
        )

        if parent_text:

            candidates.append(
                parent_text
            )

        # ----------------------------------------------------
        # 次の兄弟
        # ----------------------------------------------------

        sibling = parent.find_next_sibling()

        if sibling:

            sibling_text = normalize_text(
                sibling.get_text(
                    " ",
                    strip=True
                )
            )

            sibling_text = clean_title(
                sibling_text
            )

            if sibling_text:

                candidates.append(
                    sibling_text
                )

    # ========================================================
    # 5. h1
    # ========================================================

    for h1 in soup.find_all("h1"):

        value = normalize_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

        value = clean_title(
            value
        )

        if value:

            candidates.append(
                value
            )

    # ========================================================
    # 候補から最適なものを選ぶ
    # ========================================================

    unique_candidates = []

    for candidate in candidates:

        candidate = normalize_text(
            candidate
        )

        if not candidate:
            continue

        if candidate in unique_candidates:
            continue

        unique_candidates.append(
            candidate
        )

    # 「内容紹介」などを除外
    unique_candidates = [
        candidate
        for candidate in unique_candidates
        if candidate not in {
            "内容紹介",
            "商品情報",
            "商品詳細",
            "詳細",
        }
    ]

    if unique_candidates:

        # 一般的に商品名は短すぎず、
        # サイトタイトル全文よりも書名らしいものを優先
        for candidate in unique_candidates:

            if len(candidate) >= 2:

                return candidate

        return unique_candidates[0]

    return ""


# ============================================================
# 発売日取得
# ============================================================

def get_release_date(text):
    """
    発売日を取得する。
    """

    # YYYY/MM/DD発売
    match = re.search(
        r"(\d{4})/(\d{1,2})/(\d{1,2})発売",
        text
    )

    if match:

        return (
            f"{match.group(1)}-"
            f"{int(match.group(2)):02d}-"
            f"{int(match.group(3)):02d}"
        )

    # YYYY年MM月DD日
    match = re.search(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        text
    )

    if match:

        return (
            f"{match.group(1)}-"
            f"{int(match.group(2)):02d}-"
            f"{int(match.group(3)):02d}"
        )

    return ""


# ============================================================
# ISBN取得
# ============================================================

def get_isbn(text):
    """
    ISBNを取得する。
    """

    # ハイフンあり
    match = re.search(
        r"ISBN\s*[:：]?\s*"
        r"(97[89][\d-]{10,20})",
        text
    )

    if match:

        return (
            match.group(1)
            .replace("-", "")
        )

    # ISBN 13桁
    match = re.search(
        r"\b(97[89]\d{10})\b",
        text
    )

    if match:

        return match.group(1)

    return ""


# ============================================================
# 価格取得
# ============================================================

def get_price(text):
    """
    価格を取得する。
    """

    match = re.search(
        r"¥\s*([\d,]+)",
        text
    )

    if match:

        return (
            match.group(1)
            .replace(",", "")
        )

    # 円表記
    match = re.search(
        r"([\d,]+)\s*円",
        text
    )

    if match:

        return (
            match.group(1)
            .replace(",", "")
        )

    return ""


# ============================================================
# 商品詳細取得
# ============================================================

def get_book_detail(url):
    """
    商品詳細ページを開いて、
    入江亜季1人の書籍だけ取得する。
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

    # ========================================================
    # 著者確認
    # ========================================================

    if not is_target_author_only(
        soup
    ):

        return None

    # ========================================================
    # タイトル
    # ========================================================

    title = get_product_title(
        soup
    )

    if not title:

        print(
            "  → 書籍名を取得できないため除外"
        )

        return None

    # ========================================================
    # 発売日
    # ========================================================

    date = get_release_date(
        text
    )

    if not date:

        print(
            "  → 発売日を取得できないため除外"
        )

        return None

    # ========================================================
    # ISBN
    # ========================================================

    isbn = get_isbn(
        text
    )

    # ========================================================
    # 価格
    # ========================================================

    price = get_price(
        text
    )

    # ========================================================
    # データ作成
    # ========================================================

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


# ============================================================
# 書籍取得
# ============================================================

def get_books():
    """
    雪割草の商品一覧から商品を取得し、
    商品詳細ページで著者を確認する。
    """

    product_links = get_product_links()

    books = []

    print()
    print(
        f"{len(product_links)}件の商品を確認します。"
    )

    print()

    for index, url in enumerate(
        product_links,
        start=1
    ):

        print(
            f"[{index}/{len(product_links)}]"
        )

        print(
            f"確認中: {url}"
        )

        try:

            book = get_book_detail(
                url
            )

            if book is None:

                print(
                    "  → 対象外"
                )

                print()

                continue

            books.append(
                book
            )

            print(
                f"  → 採用: {book['title']}"
            )

            print(
                f"  → 発売日: {book['date']}"
            )

            print(
                f"  → ISBN: {book['isbn']}"
            )

            print(
                f"  → 価格: {book['price']}円"
            )

        except requests.RequestException as e:

            print(
                f"  → 通信エラー: {e}"
            )

        except Exception as e:

            print(
                f"  → エラー: {e}"
            )

        print()

    return books


# ============================================================
# 保存済みニュース読み込み
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

            data = json.load(
                f
            )

        if isinstance(data, list):

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

def save_books(new_books):
    """
    取得した出版情報を
    既存のnews.jsonに追加する。

    同じURLは重複登録しない。
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

    return (
        added_count,
        len(saved_news)
    )


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print(
        "雪割草を確認しています..."
    )

    print(
        f"対象著者: {TARGET_AUTHOR}"
    )

    print(
        "条件: 著者が入江亜季1人だけ"
    )

    print(
        f"保存先: {DATA_FILE}"
    )

    print()

    try:

        # ====================================================
        # 商品取得
        # ====================================================

        books = get_books()

        print()

        print(
            "=" * 60
        )

        print(
            "取得結果"
        )

        print(
            "=" * 60
        )

        if not books:

            print(
                "入江亜季さんの出版情報は"
                "見つかりませんでした。"
            )

        else:

            print(
                f"入江亜季さんの出版情報: "
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

            # =================================================
            # news.jsonへ保存
            # =================================================

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