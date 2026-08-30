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

BASE_URL = "https://www.animatetimes.com"


# ------------------------------------------------------------
# 検索対象キーワード
# ------------------------------------------------------------

TARGET_KEYWORDS = [
    "入江亜季",
    "北北西に曇と往け",
]


# ------------------------------------------------------------
# アニメイトタイムズのタグページ
# ------------------------------------------------------------

TAG_URLS = {
    "入江亜季":
        "https://www.animatetimes.com/tag/details.php?id=28352",

    "北北西に曇と往け":
        "https://www.animatetimes.com/tag/details.php?id=28281",
}


# ------------------------------------------------------------
# news.json
#
# collectors/animatetimes.py
#       ↓
# プロジェクトルート
#       ↓
# data/news.json
# ------------------------------------------------------------

NEWS_JSON = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "data",
    "news.json"
)


# ------------------------------------------------------------
# 通常アクセス間隔
# ------------------------------------------------------------

REQUEST_INTERVAL = 2


# ------------------------------------------------------------
# 最大再試行回数
# ------------------------------------------------------------

MAX_RETRIES = 3


# ------------------------------------------------------------
# 403待機時間
# ------------------------------------------------------------

FORBIDDEN_WAIT_TIMES = [
    30,
    60,
    120
]


# ------------------------------------------------------------
# 429待機時間
# ------------------------------------------------------------

TOO_MANY_REQUESTS_WAIT_TIMES = [
    60,
    120,
    180
]


# ------------------------------------------------------------
# HTTPヘッダー
# ------------------------------------------------------------

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
# news.json読み込み
# ============================================================

def load_existing_news():

    if not os.path.exists(
        NEWS_JSON
    ):

        print(
            "news.jsonが存在しません。"
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

    try:

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

            normalized_url = url.rstrip(
                "/"
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

        # 日付の新しい順
        unique_news.sort(
            key=lambda x: x.get(
                "date",
                ""
            ),
            reverse=True
        )

        # dataフォルダを作成
        os.makedirs(
            os.path.dirname(
                NEWS_JSON
            ),
            exist_ok=True
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
                url.rstrip("/")
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

            print(
                f"  → アクセス: {url}"
            )

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
            # 403
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
            # 429
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
            # その他HTTPエラー
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
# タイトルから対象キーワードを確認
# ============================================================

def get_matched_keywords_from_title(title):

    matched_keywords = []

    normalized_title = normalize_text(
        title
    )

    for keyword in TARGET_KEYWORDS:

        if keyword in normalized_title:

            matched_keywords.append(
                keyword
            )

    return matched_keywords


# ============================================================
# タグページから記事URLを取得
# ============================================================

def get_article_links_from_tag(
    tag_url,
    keyword
):

    response = request_page(
        tag_url
    )

    if response is None:

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    article_links = []

    seen_urls = set()

    # --------------------------------------------------------
    # 記事リンクを探す
    # --------------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        )

        if not href:
            continue

        # アニメイトタイムズの記事URL
        if "/news/details.php?id=" not in href:
            continue

        article_url = urljoin(
            BASE_URL,
            href
        )

        article_url = article_url.rstrip(
            "/"
        )

        if article_url in seen_urls:
            continue

        seen_urls.add(
            article_url
        )

        article_links.append(
            article_url
        )

    print(
        f"  → タグページから"
        f"{len(article_links)}件の記事URLを取得"
    )

    return article_links


# ============================================================
# 記事ページからタイトル取得
# ============================================================

def get_article_title(soup):

    # --------------------------------------------------------
    # h1
    # --------------------------------------------------------

    h1 = soup.find(
        "h1"
    )

    if h1:

        title = normalize_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

        if title:

            return title

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

            return title

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

        if title:

            return title

    return ""


# ============================================================
# 記事本文から日付取得
# ============================================================

def get_article_date(soup):

    # --------------------------------------------------------
    # timeタグ
    # --------------------------------------------------------

    for time_tag in soup.find_all(
        "time"
    ):

        date_text = normalize_text(
            time_tag.get_text(
                " ",
                strip=True
            )
        )

        match = re.search(
            r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
            date_text
        )

        if match:

            return (
                f"{match.group(1)}-"
                f"{int(match.group(2)):02d}-"
                f"{int(match.group(3)):02d}"
            )

        # datetime属性
        datetime_value = time_tag.get(
            "datetime",
            ""
        )

        if datetime_value:

            match = re.search(
                r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
                datetime_value
            )

            if match:

                return (
                    f"{match.group(1)}-"
                    f"{int(match.group(2)):02d}-"
                    f"{int(match.group(3)):02d}"
                )

    # --------------------------------------------------------
    # ページ全体から日付を探す
    # --------------------------------------------------------

    page_text = normalize_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    match = re.search(
        r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        page_text
    )

    if match:

        return (
            f"{match.group(1)}-"
            f"{int(match.group(2)):02d}-"
            f"{int(match.group(3)):02d}"
        )

    return ""


# ============================================================
# 記事ページからデータ取得
# ============================================================

def get_article_detail(
    url,
    tag_keywords
):

    response = request_page(
        url
    )

    if response is None:

        return None, "アクセス失敗"

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # ========================================================
    # タイトル
    # ========================================================

    title = get_article_title(
        soup
    )

    if not title:

        print(
            "  → タイトルを取得できないため除外"
        )

        return None, "タイトル取得失敗"

    print(
        f"  → タイトル: {title}"
    )

    # ========================================================
    # タイトルによる厳密な対象判定
    # ========================================================

    matched_keywords = (
        get_matched_keywords_from_title(
            title
        )
    )

    # --------------------------------------------------------
    # タイトルに対象キーワードがない
    #
    # タグページに掲載されていても除外する
    # --------------------------------------------------------

    if not matched_keywords:

        print(
            "  → タイトルに"
            "「入江亜季」または"
            "「北北西に曇と往け」がないため除外"
        )

        return None, "タイトル対象外"

    # --------------------------------------------------------
    # タグページ側のキーワードとの関係も表示
    # --------------------------------------------------------

    print(
        f"  → タイトルに含まれる対象キーワード: "
        f"{', '.join(matched_keywords)}"
    )

    # ========================================================
    # 日付
    # ========================================================

    date = get_article_date(
        soup
    )

    # ========================================================
    # データ作成
    # ========================================================

    keyword_text = ", ".join(
        matched_keywords
    )

    article = {
        "date": date,
        "title": title,
        "source": "アニメイトタイムズ",
        "category": "ニュース",
        "author": "入江亜季",
        "url": url,
        "keyword": keyword_text
    }

    return article, "取得成功"


# ============================================================
# アニメイトタイムズ取得
# ============================================================

def get_articles():

    # --------------------------------------------------------
    # 既存データ読み込み
    # --------------------------------------------------------

    existing_news = load_existing_news()

    existing_urls = get_existing_urls(
        existing_news
    )

    print(
        f"既存データのURL: "
        f"{len(existing_urls)}件"
    )

    print()

    # --------------------------------------------------------
    # タグページから記事URLを取得
    # --------------------------------------------------------

    # URL:
    #   {
    #       記事URL:
    #           [検索キーワード1, 検索キーワード2]
    #   }
    #
    # 同じ記事が2つのタグに存在しても
    # URLを1つにまとめる
    # --------------------------------------------------------

    url_keywords = {}

    for keyword in TARGET_KEYWORDS:

        tag_url = TAG_URLS.get(
            keyword
        )

        if not tag_url:

            print(
                f"タグURLが設定されていません: "
                f"{keyword}"
            )

            continue

        print()
        print(
            "=" * 60
        )

        print(
            f"検索対象: {keyword}"
        )

        print(
            f"タグページ: {tag_url}"
        )

        print(
            "=" * 60
        )

        links = get_article_links_from_tag(
            tag_url,
            keyword
        )

        for url in links:

            if url not in url_keywords:

                url_keywords[url] = []

            if keyword not in url_keywords[url]:

                url_keywords[url].append(
                    keyword
                )

    # --------------------------------------------------------
    # URL重複除去
    # --------------------------------------------------------

    article_links = list(
        url_keywords.keys()
    )

    print()
    print(
        "=" * 60
    )

    print(
        f"タグページから取得した"
        f"ユニーク記事URL: "
        f"{len(article_links)}件"
    )

    print(
        "=" * 60
    )

    print()

    articles = []

    failed_urls = []

    skipped_existing = 0

    checked_new = 0

    excluded_by_title = 0

    # --------------------------------------------------------
    # 各記事を確認
    # --------------------------------------------------------

    for index, url in enumerate(
        article_links,
        start=1
    ):

        print(
            f"[{index}/{len(article_links)}]"
        )

        # ====================================================
        # 既に保存済み
        # ====================================================

        if url.rstrip("/") in existing_urls:

            print(
                f"スキップ（保存済み）: "
                f"{url}"
            )

            skipped_existing += 1

            continue

        # ====================================================
        # 新規記事
        # ====================================================

        print(
            f"確認中: {url}"
        )

        checked_new += 1

        tag_keywords = url_keywords[
            url
        ]

        print(
            f"  → タグ側のキーワード: "
            f"{', '.join(tag_keywords)}"
        )

        try:

            article, status = get_article_detail(
                url,
                tag_keywords
            )

            # ------------------------------------------------
            # 採用
            # ------------------------------------------------

            if article is not None:

                articles.append(
                    article
                )

                print(
                    f"  → 採用: "
                    f"{article['title']}"
                )

            # ------------------------------------------------
            # タイトル対象外
            # ------------------------------------------------

            elif status == "タイトル対象外":

                excluded_by_title += 1

                print(
                    "  → タイトル条件により除外"
                )

            # ------------------------------------------------
            # アクセス失敗
            # ------------------------------------------------

            elif status == "アクセス失敗":

                failed_urls.append(
                    url
                )

                print(
                    "  → 今回は取得できませんでした"
                )

        except Exception as e:

            print(
                f"  → エラー: {e}"
            )

            failed_urls.append(
                url
            )

        print()

    return (
        articles,
        failed_urls,
        skipped_existing,
        checked_new,
        excluded_by_title,
        existing_news
    )


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print(
        "アニメイトタイムズを確認しています..."
    )

    print()

    print(
        "【検索対象】"
    )

    for keyword in TARGET_KEYWORDS:

        print(
            f"  ・{keyword}"
        )

    print()

    print(
        "【取得条件】"
    )

    print(
        "  ・タグページから記事URLを取得"
    )

    print(
        "  ・記事URLの重複を除去"
    )

    print(
        "  ・既にnews.jsonにあるURLはアクセスしない"
    )

    print(
        "  ・記事タイトルに"
        "「入江亜季」または"
        "「北北西に曇と往け」がある記事だけ採用"
    )

    print()

    print(
        f"保存先: {NEWS_JSON}"
    )

    print()

    try:

        (
            articles,
            failed_urls,
            skipped_existing,
            checked_new,
            excluded_by_title,
            existing_news
        ) = get_articles()

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
            f"今回新規取得した記事: "
            f"{len(articles)}件"
        )

        print(
            f"既に保存済みでスキップ: "
            f"{skipped_existing}件"
        )

        print(
            f"今回記事ページを確認した件数: "
            f"{checked_new}件"
        )

        print(
            f"タイトル条件で除外: "
            f"{excluded_by_title}件"
        )

        print(
            f"取得できなかった記事: "
            f"{len(failed_urls)}件"
        )

        print()

        # ====================================================
        # 今回取得した記事
        # ====================================================

        if articles:

            print(
                "【今回新しく取得した記事】"
            )

            print()

            for article in articles:

                print(
                    f"日付: "
                    f"{article['date']}"
                )

                print(
                    f"タイトル: "
                    f"{article['title']}"
                )

                print(
                    f"キーワード: "
                    f"{article['keyword']}"
                )

                print(
                    f"URL: "
                    f"{article['url']}"
                )

                print(
                    "-" * 60
                )

        else:

            print(
                "今回、新しい記事はありませんでした。"
            )

        # ====================================================
        # news.jsonへ保存
        # ====================================================

        if articles:

            print()

            print(
                "data/news.jsonへ"
                "新しいデータを追加しています..."
            )

            # 既存データ + 今回取得したデータ
            updated_news = (
                existing_news + articles
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
                "【今回取得できなかった記事】"
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