import json
import os
import sys
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

# ------------------------------------------------------------
# 保存対象にするタイトルキーワード
# ------------------------------------------------------------

TITLE_KEYWORDS = [
    "入江亜季",
    "北北西に曇と往け",
]

MAX_RETRIES = 3

WAIT_TIMES = [
    10,
    30,
    60,
]

# data/news.json
NEWS_JSON = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "data",
    "news.json",
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
# タイトルが保存対象か判定
# ============================================================

def is_target_title(title):

    if not title:
        return False

    for keyword in TITLE_KEYWORDS:

        if keyword in title:

            return True

    return False


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
                timeout=30,
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

    source = item.get(
        "source",
        ""
    ).strip().lower()

    source_url = item.get(
        "source_url",
        ""
    ).strip().lower()

    return (
        source == "ナタリー"
        or source == "コミックナタリー"
        or source_url == "https://natalie.mu"
        or source_url == "https://natalie.mu/"
    )


# ============================================================
# コミックナタリーURL判定
# ============================================================

def is_natalie_comic_url(url):

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
# Google News URLから元記事URL取得
# ============================================================

def resolve_google_news_url(
    google_news_url
):

    if not google_news_url:

        return ""

    print()
    print(
        "Google News URLから"
        "元記事URLを取得中..."
    )

    print(
        f"Google News URL: "
        f"{google_news_url}"
    )

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    # --------------------------------------------------------
    # Google News記事ページ取得
    # --------------------------------------------------------

    try:

        response = session.get(
            google_news_url,
            timeout=30,
        )

    except requests.RequestException as e:

        print(
            f"Google Newsページ取得エラー: {e}"
        )

        return ""

    print(
        f"Google Newsページ: "
        f"HTTP {response.status_code}"
    )

    if response.status_code != 200:

        return ""

    # --------------------------------------------------------
    # まずリダイレクト後URLを確認
    # --------------------------------------------------------

    final_url = response.url

    if is_natalie_comic_url(
        final_url
    ):

        print(
            f"リダイレクト先から取得: "
            f"{final_url}"
        )

        return final_url

    # --------------------------------------------------------
    # HTML内のナタリーURLを探す
    # --------------------------------------------------------

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # aタグ
    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a.get(
            "href"
        )

        if not href:
            continue

        if is_natalie_comic_url(
            href
        ):

            print(
                f"aタグから取得: "
                f"{href}"
            )

            return href

    # --------------------------------------------------------
    # canonical
    # --------------------------------------------------------

    canonical = soup.find(
        "link",
        rel="canonical"
    )

    if canonical:

        href = canonical.get(
            "href",
            ""
        )

        if is_natalie_comic_url(
            href
        ):

            print(
                f"canonicalから取得: "
                f"{href}"
            )

            return href

    # --------------------------------------------------------
    # og:url
    # --------------------------------------------------------

    og_url = soup.find(
        "meta",
        property="og:url"
    )

    if og_url:

        content = og_url.get(
            "content",
            ""
        )

        if is_natalie_comic_url(
            content
        ):

            print(
                f"og:urlから取得: "
                f"{content}"
            )

            return content

    print(
        "元記事URLを取得できませんでした。"
    )

    return ""


# ============================================================
# 日付変換
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

            pass

    return pub_date[:10]


# ============================================================
# news.json読み込み
# ============================================================

def load_news():

    print()
    print(
        f"news.json読み込み: "
        f"{NEWS_JSON}"
    )

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
                "news.jsonの形式が不正です。"
            )

            return []

        return data

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
# 記事データ作成
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
# メイン
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print(
        "コミックナタリー"
        " Google News RSS取得"
    )
    print("=" * 70)

    print()
    print(
        f"保存先: {NEWS_JSON}"
    )

    # --------------------------------------------------------
    # news.json
    # --------------------------------------------------------

    news = load_news()

    print()
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

    # --------------------------------------------------------
    # RSS検索
    # --------------------------------------------------------

    success_count = 0

    natalie_candidates = []

    checked_google_urls = set()

    title_excluded_count = 0

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

        success_count += 1

        try:

            results = parse_rss(
                response
            )

            # ------------------------------------------------
            # 記事を確認
            # ------------------------------------------------

            for item in results:

                # --------------------------------------------
                # ナタリー判定
                # --------------------------------------------

                if not is_natalie_source(
                    item
                ):

                    continue

                # --------------------------------------------
                # ★ タイトルフィルタ
                # --------------------------------------------

                if not is_target_title(
                    item["title"]
                ):

                    title_excluded_count += 1

                    print()
                    print(
                        "→ タイトル条件外のため除外"
                    )

                    print(
                        f"タイトル: "
                        f"{item['title']}"
                    )

                    continue

                google_url = item[
                    "link"
                ]

                if not google_url:

                    continue

                # --------------------------------------------
                # Google News URL重複
                # --------------------------------------------

                if google_url in checked_google_urls:

                    continue

                checked_google_urls.add(
                    google_url
                )

                natalie_candidates.append(
                    item
                )

                print()
                print(
                    "★ 保存対象タイトル"
                )

                print(
                    f"タイトル: "
                    f"{item['title']}"
                )

        except Exception as e:

            print()
            print(
                f"RSS解析エラー: {e}"
            )

        # ----------------------------------------------------
        # 検索ワード間隔
        # ----------------------------------------------------

        if search_word != SEARCH_WORDS[-1]:

            time.sleep(
                3
            )

    # ========================================================
    # タイトルフィルタ結果
    # ========================================================

    print()
    print("=" * 70)
    print("タイトルフィルタ結果")
    print("=" * 70)

    print(
        f"タイトル条件を通過: "
        f"{len(natalie_candidates)}件"
    )

    print(
        f"タイトル条件で除外: "
        f"{title_excluded_count}件"
    )

    # ========================================================
    # 元記事URL取得
    # ========================================================

    resolved_results = []

    print()
    print("=" * 70)
    print(
        "Google News → "
        "コミックナタリーURL変換"
    )
    print("=" * 70)

    for index, item in enumerate(
        natalie_candidates,
        start=1
    ):

        print()
        print(
            "-" * 70
        )

        print(
            f"[{index}/{len(natalie_candidates)}]"
        )

        print(
            f"タイトル: "
            f"{item['title']}"
        )

        # ----------------------------------------------------
        # 元記事URL
        # ----------------------------------------------------

        article_url = resolve_google_news_url(
            item["link"]
        )

        if not article_url:

            print(
                "→ 元記事URL取得失敗"
            )

            continue

        # ----------------------------------------------------
        # コミックナタリー確認
        # ----------------------------------------------------

        if not is_natalie_comic_url(
            article_url
        ):

            print(
                "→ コミックナタリーURLではないため"
                "スキップ"
            )

            print(
                f"取得URL: "
                f"{article_url}"
            )

            continue

        print(
            "★ コミックナタリー記事として確定"
        )

        # ----------------------------------------------------
        # 既存URL
        # ----------------------------------------------------

        if article_url in existing_urls:

            print(
                "→ 既にnews.jsonに存在"
            )

            continue

        resolved_results.append({
            "item": item,
            "article_url": article_url,
        })

        time.sleep(
            1
        )

    # ========================================================
    # news.jsonへ追加
    # ========================================================

    print()
    print("=" * 70)
    print("news.jsonへの保存")
    print("=" * 70)

    new_count = 0

    duplicate_count = 0

    for result in resolved_results:

        item = result[
            "item"
        ]

        article_url = result[
            "article_url"
        ]

        if article_url in existing_urls:

            duplicate_count += 1

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
            "★ 新規追加"
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
    # 日付順
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
            "data/news.jsonを更新しました。"
        )

    else:

        print()
        print(
            "新規追加する記事はありません。"
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
        f"タイトル条件通過: "
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

    print(
        f"重複スキップ: "
        f"{duplicate_count}件"
    )

    print(
        f"news.json合計: "
        f"{len(news)}件"
    )

    print()

    if success_count == len(
        SEARCH_WORDS
    ):

        print(
            "すべてのRSS検索に成功しました。"
        )

    else:

        print(
            "一部のRSS検索に失敗しました。"
        )

        sys.exit(1)