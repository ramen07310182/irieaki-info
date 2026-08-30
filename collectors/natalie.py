import base64
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q={}&hl=ja&gl=JP&ceid=JP:ja"
)

SEARCH_WORDS = [
    "入江亜季 site:natalie.mu/comic",
    "北北西に曇と往け site:natalie.mu/comic",
]

MAX_RETRIES = 3

WAIT_TIMES = [
    10,
    30,
    60,
]

# ------------------------------------------------------------
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, "
        "application/xml, "
        "text/xml, "
        "text/html;q=0.9, "
        "*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


# ============================================================
# Google News RSS取得
# ============================================================

def get_rss(search_word):

    encoded_word = quote(
        search_word
    )

    url = GOOGLE_NEWS_RSS_URL.format(
        encoded_word
    )

    print()
    print("=" * 70)
    print("Google News RSSへアクセス")
    print("=" * 70)

    print(
        f"検索ワード: {search_word}"
    )

    print(
        f"URL: {url}"
    )

    for attempt in range(MAX_RETRIES):

        print()
        print(
            f"取得中... "
            f"（試行 {attempt + 1}/{MAX_RETRIES}）"
        )

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            print(
                f"HTTPステータス: "
                f"{response.status_code}"
            )

            if response.status_code == 200:

                print(
                    "RSSの取得に成功しました。"
                )

                return response

            if response.status_code == 403:

                print(
                    "403 Forbidden"
                )

            elif response.status_code == 429:

                print(
                    "429 Too Many Requests"
                )

            else:

                print(
                    f"HTTPエラー: "
                    f"{response.status_code}"
                )

            if attempt < MAX_RETRIES - 1:

                wait_time = WAIT_TIMES[attempt]

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

        except requests.RequestException as e:

            print(
                f"通信エラー: {e}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = WAIT_TIMES[attempt]

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(
                    wait_time
                )

    return None


# ============================================================
# RSS解析
# ============================================================

def parse_rss(response):

    soup = BeautifulSoup(
        response.content,
        "xml"
    )

    items = soup.find_all(
        "item"
    )

    print()
    print(
        f"RSS内の記事数: {len(items)}件"
    )

    results = []

    for item in items:

        title_element = item.find(
            "title"
        )

        link_element = item.find(
            "link"
        )

        pub_date_element = item.find(
            "pubDate"
        )

        source_element = item.find(
            "source"
        )

        if title_element is None:

            continue

        title = title_element.get_text(
            strip=True
        )

        link = ""

        if link_element:

            link = link_element.get_text(
                strip=True
            )

        pub_date = ""

        if pub_date_element:

            pub_date = pub_date_element.get_text(
                strip=True
            )

        source = ""

        source_url = ""

        if source_element:

            source = source_element.get_text(
                strip=True
            )

            source_url = source_element.get(
                "url",
                ""
            )

        results.append({
            "title": title,
            "link": link,
            "pub_date": pub_date,
            "source": source,
            "source_url": source_url,
        })

    return results


# ============================================================
# ナタリー判定
# ============================================================

def is_natalie_source(item):

    source = (
        item.get(
            "source",
            ""
        )
        .strip()
        .lower()
    )

    source_url = (
        item.get(
            "source_url",
            ""
        )
        .strip()
        .lower()
    )

    return (
        source == "ナタリー"
        or source == "コミックナタリー"
        or source_url == "https://natalie.mu"
        or source_url == "https://natalie.mu/"
    )


# ============================================================
# Google News URLから古い形式のURLを復元
# ============================================================

def decode_old_google_news_url(
    google_news_url
):

    if not google_news_url:

        return ""

    try:

        match = re.search(
            r"/articles/([^?]+)",
            google_news_url
        )

        if not match:

            return ""

        encoded = match.group(
            1
        )

        # URL-safe Base64
        padding = "=" * (
            (-len(encoded)) % 4
        )

        encoded += padding

        raw = base64.urlsafe_b64decode(
            encoded
        )

        text = raw.decode(
            "utf-8",
            errors="ignore"
        )

        # URL部分を探す
        url_match = re.search(
            r"https?://[^\x00-\x1f\x7f\"']+",
            text
        )

        if url_match:

            return url_match.group(
                0
            )

    except Exception:

        pass

    return ""


# ============================================================
# Google NewsのHTMLから記事URLを探す
# ============================================================

def get_url_from_google_news_page(
    google_news_url
):

    try:

        response = requests.get(
            google_news_url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

        print(
            f"Google Newsページ: "
            f"HTTP {response.status_code}"
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # ----------------------------------------------------
        # 1. aタグ
        # ----------------------------------------------------

        for a in soup.find_all(
            "a",
            href=True
        ):

            href = a.get(
                "href"
            )

            if not href:

                continue

            if is_natalie_url(
                href
            ):

                return href

        # ----------------------------------------------------
        # 2. canonical
        # ----------------------------------------------------

        canonical = soup.find(
            "link",
            rel="canonical"
        )

        if canonical:

            href = canonical.get(
                "href",
                ""
            )

            if is_natalie_url(
                href
            ):

                return href

        # ----------------------------------------------------
        # 3. og:url
        # ----------------------------------------------------

        og_url = soup.find(
            "meta",
            property="og:url"
        )

        if og_url:

            content = og_url.get(
                "content",
                ""
            )

            if is_natalie_url(
                content
            ):

                return content

    except Exception as e:

        print(
            f"Google Newsページ解析エラー: {e}"
        )

    return ""


# ============================================================
# Google News URLから元記事URLを取得
# ============================================================

def resolve_article_url(
    google_news_url
):

    if not google_news_url:

        return ""

    print()
    print(
        "元記事URLを取得中..."
    )

    print(
        f"Google News URL: "
        f"{google_news_url}"
    )

    # --------------------------------------------------------
    # 方法1
    # 古いGoogle News形式のBase64
    # --------------------------------------------------------

    decoded_url = decode_old_google_news_url(
        google_news_url
    )

    if decoded_url:

        print(
            f"Base64から取得: "
            f"{decoded_url}"
        )

        if is_natalie_url(
            decoded_url
        ):

            print(
                "★ 元記事URLを取得しました。"
            )

            return decoded_url

    # --------------------------------------------------------
    # 方法2
    # Google NewsページのHTML
    # --------------------------------------------------------

    page_url = get_url_from_google_news_page(
        google_news_url
    )

    if page_url:

        print(
            f"HTMLから取得: "
            f"{page_url}"
        )

        print(
            "★ 元記事URLを取得しました。"
        )

        return page_url

    # --------------------------------------------------------
    # 取得失敗
    # --------------------------------------------------------

    print(
        "元記事URLを取得できませんでした。"
    )

    return ""


# ============================================================
# natalie.mu URL判定
# ============================================================

def is_natalie_url(url):

    if not url:

        return False

    try:

        parsed = urlparse(
            url
        )

        hostname = (
            parsed.hostname or ""
        ).lower()

        path = (
            parsed.path or ""
        ).lower()

        return (
            hostname == "natalie.mu"
            and path.startswith(
                "/comic/"
            )
        )

    except Exception:

        return False


# ============================================================
# RSS日時 → YYYY-MM-DD
# ============================================================

def convert_date(pub_date):

    if not pub_date:

        return ""

    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
    ]

    for fmt in formats:

        try:

            dt = datetime.strptime(
                pub_date,
                fmt
            )

            return dt.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            continue

    return pub_date[:10]


# ============================================================
# news.json読み込み
# ============================================================

def load_news():

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

        if isinstance(
            data,
            list
        ):

            return data

        print(
            "news.jsonの形式が不正です。"
        )

        return []

    except Exception as e:

        print(
            f"news.json読み込みエラー: {e}"
        )

        return []


# ============================================================
# news.json保存
# ============================================================

def save_news(news):

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
            news,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write(
            "\n"
        )


# ============================================================
# 新しい記事データ作成
# ============================================================

def create_news_item(
    item,
    article_url
):

    return {
        "date": convert_date(
            item["pub_date"]
        ),
        "title": item["title"],
        "source": "コミックナタリー",
        "category": "ニュース",
        "author": "入江亜季",
        "url": article_url,
        "keyword": "入江亜季, 北北西に曇と往け",
    }


# ============================================================
# news.jsonへ追加
# ============================================================

def save_results(
    results
):

    print()
    print("=" * 70)
    print("news.jsonへの保存")
    print("=" * 70)

    news = load_news()

    print(
        f"既存記事数: {len(news)}件"
    )

    existing_urls = set()

    for item in news:

        url = item.get(
            "url",
            ""
        )

        if url:

            existing_urls.add(
                url
            )

    new_count = 0
    duplicate_count = 0

    for result in results:

        item = result[
            "item"
        ]

        article_url = result[
            "article_url"
        ]

        if not article_url:

            continue

        if article_url in existing_urls:

            duplicate_count += 1

            print()
            print(
                "重複のためスキップ:"
            )

            print(
                item["title"]
            )

            continue

        news_item = create_news_item(
            item,
            article_url
        )

        news.append(
            news_item
        )

        existing_urls.add(
            article_url
        )

        new_count += 1

        print()
        print(
            "★ 新規追加:"
        )

        print(
            f"日付: "
            f"{news_item['date']}"
        )

        print(
            f"タイトル: "
            f"{news_item['title']}"
        )

        print(
            f"URL: "
            f"{news_item['url']}"
        )

    # --------------------------------------------------------
    # 日付の新しい順に並べる
    # --------------------------------------------------------

    news.sort(
        key=lambda x: x.get(
            "date",
            ""
        ),
        reverse=True
    )

    if new_count > 0:

        save_news(
            news
        )

        print()
        print(
            f"data/news.jsonを更新しました。"
        )

    else:

        print()
        print(
            "新規追加する記事はありません。"
        )

    print()
    print(
        f"news.jsonへ新規追加: "
        f"{new_count}件"
    )

    print(
        f"重複スキップ: "
        f"{duplicate_count}件"
    )

    print(
        f"news.json合計: "
        f"{len(news)}件"
    )

    return new_count


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "コミックナタリー"
        " Google News RSS取得"
    )

    print()

    print(
        f"保存先: {NEWS_JSON}"
    )

    print()

    success_count = 0

    natalie_candidates = []

    # ========================================================
    # RSS検索
    # ========================================================

    for search_word in SEARCH_WORDS:

        response = get_rss(
            search_word
        )

        if response is None:

            print()
            print(
                f"取得失敗: "
                f"{search_word}"
            )

            continue

        try:

            results = parse_rss(
                response
            )

            success_count += 1

            print()
            print(
                f"検索結果: {len(results)}件"
            )

            # ------------------------------------------------
            # ナタリーだけ抽出
            # ------------------------------------------------

            for item in results:

                print()
                print(
                    "-" * 70
                )

                print(
                    f"タイトル: "
                    f"{item['title']}"
                )

                print(
                    f"配信元: "
                    f"{item['source']}"
                )

                print(
                    f"配信元URL: "
                    f"{item['source_url']}"
                )

                # ------------------------------------------------
                # sourceでナタリー判定
                # ------------------------------------------------

                if not is_natalie_source(
                    item
                ):

                    print(
                        "→ ナタリーではないためスキップ"
                    )

                    continue

                print(
                    "★ ナタリー記事として判定"
                )

                natalie_candidates.append(
                    item
                )

        except Exception as e:

            print()
            print(
                "RSS解析中にエラーが発生しました。"
            )

            print(
                f"エラー: {e}"
            )

        if search_word != SEARCH_WORDS[-1]:

            time.sleep(
                3
            )

    # ========================================================
    # 元記事URL取得
    # ========================================================

    print()
    print("=" * 70)
    print("コミックナタリー記事のURL取得")
    print("=" * 70)

    resolved_results = []

    # 同じ記事が複数検索で出た場合
    checked_google_urls = set()

    for item in natalie_candidates:

        google_news_url = item[
            "link"
        ]

        if google_news_url in checked_google_urls:

            continue

        checked_google_urls.add(
            google_news_url
        )

        print()
        print(
            f"タイトル: "
            f"{item['title']}"
        )

        article_url = resolve_article_url(
            google_news_url
        )

        if article_url:

            print(
                "★ コミックナタリーURL取得成功"
            )

            resolved_results.append({
                "item": item,
                "article_url": article_url,
            })

        else:

            print(
                "→ 元記事URL取得失敗"
            )

        # Googleへの連続アクセスを避ける
        time.sleep(
            1
        )

    # ========================================================
    # news.json保存
    # ========================================================

    new_count = save_results(
        resolved_results
    )

    # ========================================================
    # 最終結果
    # ========================================================

    print()
    print("=" * 70)
    print("最終結果")
    print("=" * 70)

    print(
        f"RSS取得成功: "
        f"{success_count}/{len(SEARCH_WORDS)}"
    )

    print(
        f"ナタリー候補: "
        f"{len(natalie_candidates)}件"
    )

    print(
        f"元記事URL取得成功: "
        f"{len(resolved_results)}件"
    )

    print(
        f"news.jsonへ新規追加: "
        f"{new_count}件"
    )

    print()

    if success_count == len(
        SEARCH_WORDS
    ):

        print(
            "すべてのRSS検索に成功しました。"
        )

    elif success_count > 0:

        print(
            "一部のRSS検索に成功しました。"
        )

    else:

        print(
            "RSS検索にすべて失敗しました。"
        )

        raise SystemExit(1)
