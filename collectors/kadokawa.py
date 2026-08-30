import json
import os
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

BASE_URL = "https://store.kadokawa.co.jp"

SEARCH_URL = (
    "https://store.kadokawa.co.jp/shop/goods/search.aspx"
    "?keyword=%E5%85%A5%E6%B1%9F%E3%80%80%E4%BA%9C%E5%AD%A3"
    "&search=x"
)

# 対象著者
TARGET_AUTHOR = "入江 亜季"


# ============================================================
# dataフォルダ
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)


# ============================================================
# news.json
# ============================================================

NEWS_JSON = os.path.join(
    DATA_DIR,
    "news.json"
)


# ============================================================
# KADOKAWA確認済みURL
# ============================================================

KADOKAWA_CHECKED_JSON = os.path.join(
    DATA_DIR,
    "kadokawa_checked.json"
)


# ============================================================
# 通常アクセス間隔
# ============================================================

REQUEST_INTERVAL = 2


# ============================================================
# 最大再試行回数
# ============================================================

MAX_RETRIES = 3


# ============================================================
# 403が発生した場合の待機時間
# ============================================================

FORBIDDEN_WAIT_TIMES = [
    30,
    60,
    120
]


# ============================================================
# 429が発生した場合の待機時間
# ============================================================

TOO_MANY_REQUESTS_WAIT_TIMES = [
    60,
    120,
    180
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
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


# ============================================================
# Session
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ============================================================
# dataフォルダ作成
# ============================================================

def ensure_data_directory():

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )


# ============================================================
# 文字列整理
# ============================================================

def normalize_text(text):

    if text is None:
        return ""

    text = text.replace(
        "\u3000",
        " "
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ============================================================
# URL正規化
# ============================================================

def normalize_url(url):

    if not url:
        return ""

    return url.rstrip("/")


# ============================================================
# 著者名の正規化
# ============================================================

def normalize_author_name(name):

    name = normalize_text(
        name
    )

    # 半角スペース・全角スペースを削除
    name = name.replace(
        " ",
        ""
    )

    name = name.replace(
        "\u3000",
        ""
    )

    return name


# ============================================================
# news.json読み込み
# ============================================================

def load_existing_news():

    ensure_data_directory()

    if not os.path.exists(
        NEWS_JSON
    ):

        print(
            "data/news.jsonが存在しません。"
        )

        return []

    try:

        with open(
            NEWS_JSON,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(
                f
            )

        if not isinstance(
            data,
            list
        ):

            print(
                "news.jsonの形式が想定と異なります。"
            )

            return []

        print(
            f"既存news.json: {len(data)}件"
        )

        return data

    except Exception as e:

        print(
            f"news.jsonの読み込みに失敗しました: {e}"
        )

        return []


# ============================================================
# news.json保存
# ============================================================

def save_news(news_list):

    ensure_data_directory()

    try:

        # 念のためURLで重複を除去
        unique_news = []

        seen_urls = set()

        for item in news_list:

            if not isinstance(
                item,
                dict
            ):
                continue

            url = item.get(
                "url",
                ""
            )

            normalized_url = normalize_url(
                url
            )

            if normalized_url:

                if normalized_url in seen_urls:
                    continue

                seen_urls.add(
                    normalized_url
                )

            unique_news.append(
                item
            )

        # 日付の新しい順に並べる
        unique_news.sort(
            key=lambda x: x.get(
                "date",
                ""
            ),
            reverse=True
        )

        with open(
            NEWS_JSON,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                unique_news,
                f,
                ensure_ascii=False,
                indent=2
            )

        print()
        print(
            "=" * 60
        )

        print(
            "news.jsonを保存しました。"
        )

        print(
            f"保存件数: {len(unique_news)}件"
        )

        print(
            f"保存先: {NEWS_JSON}"
        )

        print(
            "=" * 60
        )

        return True

    except Exception as e:

        print(
            f"news.jsonの保存に失敗しました: {e}"
        )

        return False


# ============================================================
# KADOKAWA確認済みURL読み込み
# ============================================================

def load_checked_urls():

    ensure_data_directory()

    if not os.path.exists(
        KADOKAWA_CHECKED_JSON
    ):

        print(
            "kadokawa_checked.jsonが存在しないため、"
            "新規作成します。"
        )

        return set()

    try:

        with open(
            KADOKAWA_CHECKED_JSON,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(
                f
            )

        if not isinstance(
            data,
            list
        ):

            print(
                "kadokawa_checked.jsonの形式が想定と異なります。"
            )

            return set()

        checked_urls = set()

        for url in data:

            if not isinstance(
                url,
                str
            ):
                continue

            normalized_url = normalize_url(
                url
            )

            if normalized_url:

                checked_urls.add(
                    normalized_url
                )

        print(
            f"既存kadokawa_checked.json: "
            f"{len(checked_urls)}件"
        )

        return checked_urls

    except Exception as e:

        print(
            f"kadokawa_checked.jsonの読み込みに失敗しました: {e}"
        )

        return set()


# ============================================================
# KADOKAWA確認済みURL保存
# ============================================================

def save_checked_urls(checked_urls):

    ensure_data_directory()

    try:

        normalized_urls = set()

        for url in checked_urls:

            normalized_url = normalize_url(
                url
            )

            if normalized_url:

                normalized_urls.add(
                    normalized_url
                )

        sorted_urls = sorted(
            normalized_urls
        )

        with open(
            KADOKAWA_CHECKED_JSON,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                sorted_urls,
                f,
                ensure_ascii=False,
                indent=2
            )

        print()
        print(
            "=" * 60
        )

        print(
            "kadokawa_checked.jsonを保存しました。"
        )

        print(
            f"確認済みURL: {len(sorted_urls)}件"
        )

        print(
            f"保存先: {KADOKAWA_CHECKED_JSON}"
        )

        print(
            "=" * 60
        )

        return True

    except Exception as e:

        print(
            f"kadokawa_checked.jsonの保存に失敗しました: {e}"
        )

        return False


# ============================================================
# 既存URL一覧
# ============================================================

def get_existing_urls(news_list):

    urls = set()

    for item in news_list:

        if not isinstance(
            item,
            dict
        ):
            continue

        url = item.get(
            "url"
        )

        if url:

            urls.add(
                normalize_url(url)
            )

    return urls


# ============================================================
# HTTPアクセス
# ============================================================

def request_page(url):

    for attempt in range(
        MAX_RETRIES
    ):

        try:

            response = session.get(
                url,
                timeout=30
            )

            # ------------------------------------------------
            # 正常
            # ------------------------------------------------

            if response.status_code == 200:

                time.sleep(
                    REQUEST_INTERVAL
                )

                return response

            # ------------------------------------------------
            # 403 Forbidden
            # ------------------------------------------------

            if response.status_code == 403:

                if attempt >= MAX_RETRIES - 1:

                    print(
                        "  → 403 Forbidden"
                        "（再試行上限）"
                    )

                    return None

                wait_time = (
                    FORBIDDEN_WAIT_TIMES[
                        attempt
                    ]
                )

                print(
                    f"  → 403 Forbidden。"
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

                continue

            # ------------------------------------------------
            # 429 Too Many Requests
            # ------------------------------------------------

            if response.status_code == 429:

                if attempt >= MAX_RETRIES - 1:

                    print(
                        "  → 429 Too Many Requests"
                    )

                    return None

                retry_after = (
                    response.headers.get(
                        "Retry-After"
                    )
                )

                if retry_after:

                    try:

                        wait_time = int(
                            retry_after
                        )

                    except ValueError:

                        wait_time = (
                            TOO_MANY_REQUESTS_WAIT_TIMES[
                                attempt
                            ]
                        )

                else:

                    wait_time = (
                        TOO_MANY_REQUESTS_WAIT_TIMES[
                            attempt
                        ]
                    )

                print(
                    f"  → 429 Too Many Requests。"
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
                f"  → HTTPエラー: "
                f"{response.status_code}"
            )

            return None

        except requests.RequestException as e:

            if attempt >= MAX_RETRIES - 1:

                print(
                    f"  → 通信エラー: {e}"
                )

                return None

            wait_time = 10 * (
                attempt + 1
            )

            print(
                f"  → 通信エラー。"
                f"{wait_time}秒後に再試行します..."
            )

            time.sleep(
                wait_time
            )

    return None


# ============================================================
# 検索ページから商品URL取得
# ============================================================

def get_product_links_from_page(url):

    response = request_page(
        url
    )

    if response is None:

        return (
            [],
            None
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    product_links = []

    seen_urls = set()

    # --------------------------------------------------------
    # 商品ページURLを取得
    # --------------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/shop/g/g" not in href:
            continue

        product_url = urljoin(
            BASE_URL,
            href
        )

        product_url = normalize_url(
            product_url
        )

        if product_url in seen_urls:
            continue

        seen_urls.add(
            product_url
        )

        product_links.append(
            product_url
        )

    # --------------------------------------------------------
    # 次ページを探す
    # --------------------------------------------------------

    next_url = None

    for link in soup.find_all(
        "a",
        href=True
    ):

        link_text = normalize_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        if link_text != "次":
            continue

        href = link["href"]

        if not href:
            continue

        next_url = urljoin(
            BASE_URL,
            href
        )

        next_url = normalize_url(
            next_url
        )

        break

    return (
        product_links,
        next_url
    )


# ============================================================
# 全検索ページ巡回
# ============================================================

def get_all_product_links():

    current_url = SEARCH_URL

    visited_pages = set()

    all_product_links = []

    page_number = 1

    while current_url:

        # 同じページを再び訪問しない
        if current_url in visited_pages:

            print(
                "同じ検索ページが検出されたため、"
                "巡回を終了します。"
            )

            break

        visited_pages.add(
            current_url
        )

        print()
        print(
            "=" * 60
        )

        print(
            f"検索ページ {page_number}"
        )

        print(
            "=" * 60
        )

        print(
            current_url
        )

        product_links, next_url = (
            get_product_links_from_page(
                current_url
            )
        )

        if not product_links:

            print(
                "  → 商品URLを取得できませんでした。"
            )

            break

        print(
            f"このページの商品数: "
            f"{len(product_links)}件"
        )

        all_product_links.extend(
            product_links
        )

        # 次ページがなければ終了
        if not next_url:

            print(
                "次のページがないため終了します。"
            )

            break

        current_url = next_url

        page_number += 1

    # --------------------------------------------------------
    # URL重複削除
    # --------------------------------------------------------

    unique_links = []

    seen_urls = set()

    for url in all_product_links:

        normalized_url = normalize_url(
            url
        )

        if normalized_url in seen_urls:
            continue

        seen_urls.add(
            normalized_url
        )

        unique_links.append(
            normalized_url
        )

    print()
    print(
        "=" * 60
    )

    print(
        f"検索ページ数: {page_number}ページ"
    )

    print(
        f"取得した商品URL数: "
        f"{len(unique_links)}件"
    )

    print(
        "=" * 60
    )

    return unique_links


# ============================================================
# 著者欄から著者一覧を取得
# ============================================================

def find_authors(soup):
    """
    KADOKAWAの商品ページから著者を取得する。

    例：

        著者： 入江 亜季
        著者： 丸井 諒子
        著者： 太武 政夫

    のような形式を想定。

    「著者：」がページ内に複数あれば、
    それぞれを取得する。
    """

    authors = []

    # --------------------------------------------------------
    # 「著者：」を含むテキストを探す
    # --------------------------------------------------------

    author_labels = soup.find_all(
        string=re.compile(
            r"著者\s*[:：]"
        )
    )

    for label in author_labels:

        label_text = normalize_text(
            str(label)
        )

        # ====================================================
        # 「著者：入江 亜季」
        # ====================================================

        match = re.search(
            r"著者\s*[:：]\s*(.+)",
            label_text
        )

        if match:

            author_name = normalize_author_name(
                match.group(1)
            )

            if author_name:

                # 次の項目が同じ文字列に入っている場合を除去
                author_name = re.split(
                    r"(?:著者|発売日|価格|商品形態|ISBN)",
                    author_name
                )[0]

                author_name = normalize_author_name(
                    author_name
                )

                if author_name:

                    if author_name not in authors:

                        authors.append(
                            author_name
                        )

                    continue

        # ====================================================
        # 「著者：」と著者名が別要素の場合
        # ====================================================

        parent = label.parent

        if parent is None:
            continue

        current = parent

        found_author = False

        # ----------------------------------------------------
        # 近くの兄弟要素を確認
        # ----------------------------------------------------

        for _ in range(5):

            current = current.find_next_sibling()

            if current is None:
                break

            sibling_text = normalize_text(
                current.get_text(
                    " ",
                    strip=True
                )
            )

            if not sibling_text:
                continue

            # 次の著者ラベルなら終了
            if "著者" in sibling_text:

                break

            author_name = normalize_author_name(
                sibling_text
            )

            if author_name:

                if author_name not in authors:

                    authors.append(
                        author_name
                    )

                found_author = True

                break

        # ----------------------------------------------------
        # siblingで見つからなかった場合
        # ----------------------------------------------------

        if not found_author:

            next_element = parent.find_next()

            if next_element:

                next_text = normalize_text(
                    next_element.get_text(
                        " ",
                        strip=True
                    )
                )

                if (
                    next_text
                    and "著者" not in next_text
                ):

                    author_name = (
                        normalize_author_name(
                            next_text
                        )
                    )

                    if author_name:

                        if author_name not in authors:

                            authors.append(
                                author_name
                            )

    # --------------------------------------------------------
    # 重複削除
    # --------------------------------------------------------

    unique_authors = []

    for author in authors:

        if author not in unique_authors:

            unique_authors.append(
                author
            )

    return unique_authors


# ============================================================
# 著者が「入江亜季1人だけ」か判定
# ============================================================

def is_target_author_only(soup):
    """
    著者が「入江亜季」1人だけの場合のみTrue。

    別の著者が1人でも存在した場合はFalse。
    """

    authors = find_authors(
        soup
    )

    print(
        f"  → 著者数: {len(authors)}"
    )

    if authors:

        print(
            f"  → 著者一覧: "
            f"{', '.join(authors)}"
        )

    # --------------------------------------------------------
    # 著者を取得できない
    # --------------------------------------------------------

    if len(authors) == 0:

        print(
            "  → 著者を確認できないため除外"
        )

        return False

    # --------------------------------------------------------
    # 著者が複数
    # --------------------------------------------------------

    if len(authors) > 1:

        print(
            "  → 複数著者のため除外"
        )

        return False

    # --------------------------------------------------------
    # 著者が1人
    # --------------------------------------------------------

    target_author = normalize_author_name(
        TARGET_AUTHOR
    )

    if authors[0] != target_author:

        print(
            f"  → 著者が対象外: "
            f"{authors[0]}"
        )

        return False

    # --------------------------------------------------------
    # 入江亜季1人だけ
    # --------------------------------------------------------

    print(
        "  → 著者が入江亜季1人なので採用"
    )

    return True


# ============================================================
# 商品タイトル取得
# ============================================================

def get_product_title(soup):

    # --------------------------------------------------------
    # OGP
    # --------------------------------------------------------

    og_title = soup.find(
        "meta",
        property="og:title"
    )

    if og_title:

        title = normalize_text(
            og_title.get(
                "content",
                ""
            )
        )

        if title:

            title = re.split(
                r"\s*:\s*本・コミック・雑誌",
                title
            )[0]

            title = re.split(
                r"\s*\|\s*カドスト",
                title
            )[0]

            title = normalize_text(
                title
            )

            if (
                title
                and title != "カドスト"
            ):

                return title

    # --------------------------------------------------------
    # h1
    # --------------------------------------------------------

    for h1 in soup.find_all(
        "h1"
    ):

        candidate = normalize_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

        if not candidate:
            continue

        if candidate == "カドスト":
            continue

        candidate = re.split(
            r"\s*:\s*本・コミック・雑誌",
            candidate
        )[0]

        candidate = re.split(
            r"\s*\|\s*カドスト",
            candidate
        )[0]

        candidate = normalize_text(
            candidate
        )

        if candidate:

            return candidate

    # --------------------------------------------------------
    # titleタグ
    # --------------------------------------------------------

    title_tag = soup.find(
        "title"
    )

    if title_tag:

        title = normalize_text(
            title_tag.get_text(
                " ",
                strip=True
            )
        )

        title = re.split(
            r"\s*:\s*本・コミック・雑誌",
            title
        )[0]

        title = re.split(
            r"\s*\|\s*カドスト",
            title
        )[0]

        title = normalize_text(
            title
        )

        if (
            title
            and title != "カドスト"
        ):

            return title

    return ""


# ============================================================
# 商品形態取得
# ============================================================

def get_product_type(soup):

    text = normalize_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    index = text.find(
        "商品形態"
    )

    if index < 0:

        return ""

    area = text[
        index:
        index + 150
    ]

    match = re.search(
        r"商品形態\s+(.+?)(?:サイズ|商品寸法|総ページ数|ISBN|発売日|$)",
        area
    )

    if match:

        return normalize_text(
            match.group(1)
        )

    return ""


# ============================================================
# 商品詳細取得
# ============================================================

def get_book_detail(url):

    response = request_page(
        url
    )

    # ========================================================
    # アクセス失敗
    # ========================================================

    if response is None:

        return None, "アクセス失敗"

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # ========================================================
    # 著者判定
    # ========================================================

    if not is_target_author_only(
        soup
    ):

        return None, "著者対象外"

    # ========================================================
    # 商品タイトル
    # ========================================================

    title = get_product_title(
        soup
    )

    if not title:

        print(
            "  → 商品名を取得できないため除外"
        )

        return None, "タイトル取得失敗"

    # ========================================================
    # 商品形態
    # ========================================================

    product_type = get_product_type(
        soup
    )

    if (
        product_type
        and "コミックス" not in product_type
    ):

        print(
            "  → 商品形態がコミックスではないため除外"
        )

        return None, "商品形態対象外"

    # ========================================================
    # ページ全体のテキスト
    # ========================================================

    text = normalize_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # ========================================================
    # 発売日
    # ========================================================

    date = ""

    date_match = re.search(
        r"発売日\s+"
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        text
    )

    if date_match:

        date = (
            f"{date_match.group(1)}-"
            f"{int(date_match.group(2)):02d}-"
            f"{int(date_match.group(3)):02d}"
        )

    # ========================================================
    # ISBN
    # ========================================================

    isbn = ""

    isbn_match = re.search(
        r"ISBNコード\s+"
        r"(97[89]\d{10})",
        text
    )

    if isbn_match:

        isbn = isbn_match.group(1)

    # ========================================================
    # 価格
    # ========================================================

    price = ""

    price_match = re.search(
        r"(\d[\d,]*)円",
        text
    )

    if price_match:

        price = (
            price_match
            .group(1)
            .replace(
                ",",
                ""
            )
        )

    # ========================================================
    # データ作成
    # ========================================================

    book = {
        "date": date,
        "title": title,
        "source": "KADOKAWA",
        "category": "出版情報",
        "author": TARGET_AUTHOR,
        "url": url,
        "isbn": isbn,
        "price": price,
        "product_type": product_type
    }

    return book, "取得成功"


# ============================================================
# KADOKAWA取得
# ============================================================

def get_books():

    # --------------------------------------------------------
    # 既存データ読み込み
    # --------------------------------------------------------

    existing_news = load_existing_news()

    existing_urls = get_existing_urls(
        existing_news
    )

    print(
        f"既存商品のURL: "
        f"{len(existing_urls)}件"
    )

    # --------------------------------------------------------
    # 確認済みURL読み込み
    # --------------------------------------------------------

    checked_urls = load_checked_urls()

    print(
        f"KADOKAWA確認済みURL: "
        f"{len(checked_urls)}件"
    )

    # --------------------------------------------------------
    # news.jsonに既にあるKADOKAWA商品を
    # 確認済みURLにも追加
    # --------------------------------------------------------

    kadokawa_news_urls = set()

    for item in existing_news:

        if not isinstance(
            item,
            dict
        ):
            continue

        if item.get(
            "source"
        ) != "KADOKAWA":

            continue

        url = item.get(
            "url",
            ""
        )

        normalized_url = normalize_url(
            url
        )

        if normalized_url:

            kadokawa_news_urls.add(
                normalized_url
            )

    if kadokawa_news_urls:

        before_count = len(
            checked_urls
        )

        checked_urls.update(
            kadokawa_news_urls
        )

        added_count = (
            len(checked_urls)
            - before_count
        )

        if added_count > 0:

            print(
                f"news.jsonから"
                f"{added_count}件を"
                f"確認済みとして登録します。"
            )

    print()

    # --------------------------------------------------------
    # 全商品URL取得
    # --------------------------------------------------------

    product_links = (
        get_all_product_links()
    )

    print()

    print(
        "=" * 60
    )

    print(
        f"{len(product_links)}件の商品URLを確認します。"
    )

    print(
        "=" * 60
    )

    print()

    books = []

    failed_urls = []

    skipped_existing = 0

    skipped_checked = 0

    checked_new = 0

    # --------------------------------------------------------
    # 各商品を確認
    # --------------------------------------------------------

    for index, url in enumerate(
        product_links,
        start=1
    ):

        normalized_url = normalize_url(
            url
        )

        print(
            f"[{index}/{len(product_links)}]"
        )

        # ====================================================
        # news.jsonに既に保存済み
        # ====================================================

        if normalized_url in existing_urls:

            print(
                f"スキップ（news.json保存済み）: "
                f"{url}"
            )

            skipped_existing += 1

            # 念のため確認済みに追加
            checked_urls.add(
                normalized_url
            )

            continue

        # ====================================================
        # 以前に商品ページを確認済み
        # ====================================================

        if normalized_url in checked_urls:

            print(
                f"スキップ（確認済み）: "
                f"{url}"
            )

            skipped_checked += 1

            continue

        # ====================================================
        # 未確認の商品
        # ====================================================

        print(
            f"確認中: {url}"
        )

        checked_new += 1

        try:

            book, status = get_book_detail(
                url
            )

            # ------------------------------------------------
            # 正常に商品ページを確認できた
            # ------------------------------------------------

            if status != "アクセス失敗":

                # --------------------------------------------
                # ここが重要
                #
                # 正常にページを取得できたので、
                # 著者対象外や商品形態対象外であっても
                # 「確認済み」とする
                # --------------------------------------------

                checked_urls.add(
                    normalized_url
                )

            # ------------------------------------------------
            # 採用
            # ------------------------------------------------

            if book is not None:

                books.append(
                    book
                )

                print(
                    f"  → 採用: "
                    f"{book['title']}"
                )

            # ------------------------------------------------
            # アクセス失敗
            # ------------------------------------------------

            elif status == "アクセス失敗":

                failed_urls.append(
                    url
                )

                print(
                    "  → 今回は取得できませんでした。"
                    "確認済みには登録しません。"
                )

        except Exception as e:

            print(
                f"  → エラー: {e}"
            )

            # エラーの場合も確認済みにしない
            failed_urls.append(
                url
            )

        print()

    return (
        books,
        failed_urls,
        skipped_existing,
        skipped_checked,
        checked_new,
        existing_news,
        checked_urls
    )


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print(
        "KADOKAWAを確認しています..."
    )

    print(
        f"対象著者: {TARGET_AUTHOR}"
    )

    print(
        "条件: 著者が入江亜季1人だけ"
    )

    print(
        f"保存先: {NEWS_JSON}"
    )

    print(
        f"確認済みURL保存先: "
        f"{KADOKAWA_CHECKED_JSON}"
    )

    print()

    try:

        (
            books,
            failed_urls,
            skipped_existing,
            skipped_checked,
            checked_new,
            existing_news,
            checked_urls
        ) = get_books()

        # ====================================================
        # 確認済みURLを保存
        # ====================================================

        save_checked_urls(
            checked_urls
        )

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

        print(
            f"今回新規取得した"
            f"入江亜季さんの商品: "
            f"{len(books)}件"
        )

        print(
            f"既にnews.jsonへ保存済みでスキップ: "
            f"{skipped_existing}件"
        )

        print(
            f"以前確認済みでスキップ: "
            f"{skipped_checked}件"
        )

        print(
            f"今回初めて商品ページを確認した件数: "
            f"{checked_new}件"
        )

        print(
            f"取得できなかった商品: "
            f"{len(failed_urls)}件"
        )

        print()

        # ====================================================
        # 今回取得した商品
        # ====================================================

        if books:

            print(
                "【今回新しく取得した商品】"
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
                    f"商品形態: "
                    f"{book['product_type']}"
                )

                print(
                    f"URL: {book['url']}"
                )

                print(
                    "-" * 60
                )

        else:

            print(
                "今回、新しい商品はありませんでした。"
            )

        # ====================================================
        # news.jsonへ保存
        # ====================================================

        if books:

            print()
            print(
                "news.jsonへ新しいデータを追加しています..."
            )

            # 既存データ + 今回取得したデータ
            updated_news = (
                existing_news + books
            )

            save_news(
                updated_news
            )

        else:

            print()
            print(
                "新しいデータがないため、"
                "news.jsonは変更しません。"
            )

        # ====================================================
        # 取得失敗URL
        # ====================================================

        if failed_urls:

            print()

            print(
                "=" * 60
            )

            print(
                "【今回取得できなかった商品】"
            )

            print(
                "=" * 60
            )

            for url in failed_urls:

                print(
                    url
                )

    except Exception as e:

        print(
            "データの取得中に"
            "エラーが発生しました。"
        )

        print(
            f"エラー: {e}"
        )