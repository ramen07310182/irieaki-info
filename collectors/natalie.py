import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import quote, urljoin, urlparse

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
    print("=" * 60)
    print("Google News RSSへアクセス")
    print("=" * 60)

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
# Google News RSSの記事解析
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

        if source_element:

            source = source_element.get_text(
                strip=True
            )

        results.append({
            "title": title,
            "link": link,
            "pub_date": pub_date,
            "source": source,
        })

    return results


# ============================================================
# コミックナタリーURL判定
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
# Google News URLから実際の記事URLを取得
# ============================================================

def resolve_google_news_url(
    google_news_url
):

    if not google_news_url:

        return ""

    print()
    print(
        "Google News URLを確認中..."
    )

    print(
        f"Google News URL: "
        f"{google_news_url}"
    )

    try:

        response = requests.get(
            google_news_url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

        print(
            f"HTTPステータス: "
            f"{response.status_code}"
        )

        # ----------------------------------------------------
        # リダイレクト後のURL
        # ----------------------------------------------------

        final_url = response.url

        print(
            f"リダイレクト先: "
            f"{final_url}"
        )

        if is_natalie_url(
            final_url
        ):

            print(
                "★ リダイレクト先は"
                "コミックナタリーです。"
            )

            return final_url

        # ----------------------------------------------------
        # HTML内のリンクを確認
        # ----------------------------------------------------

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = soup.find_all(
            "a",
            href=True
        )

        for a in links:

            href = a.get(
                "href"
            )

            if not href:

                continue

            absolute_url = urljoin(
                response.url,
                href
            )

            if is_natalie_url(
                absolute_url
            ):

                print(
                    "★ HTML内から"
                    "コミックナタリーURLを発見しました。"
                )

                print(
                    f"実際の記事URL: "
                    f"{absolute_url}"
                )

                return absolute_url

        # ----------------------------------------------------
        # meta refresh
        # ----------------------------------------------------

        meta_refresh = soup.find(
            "meta",
            attrs={
                "http-equiv": "refresh"
            }
        )

        if meta_refresh:

            content = meta_refresh.get(
                "content",
                ""
            )

            if "url=" in content.lower():

                refresh_url = content.split(
                    "=",
                    1
                )[1].strip()

                refresh_url = urljoin(
                    response.url,
                    refresh_url
                )

                if is_natalie_url(
                    refresh_url
                ):

                    print(
                        "★ Meta Refreshから"
                        "コミックナタリーURLを発見しました。"
                    )

                    return refresh_url

        print(
            "コミックナタリーのURLを"
            "確認できませんでした。"
        )

        return ""

    except requests.RequestException as e:

        print(
            f"記事URL確認中の通信エラー: {e}"
        )

        return ""

    except Exception as e:

        print(
            f"記事URL確認中のエラー: {e}"
        )

        return ""


# ============================================================
# RSS日時をYYYY-MM-DDに変換
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

            if dt.tzinfo:

                dt = dt.astimezone(
                    timezone.utc
                )

            return dt.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            continue

    # --------------------------------------------------------
    # 変換できない場合
    # --------------------------------------------------------

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
            f"news.jsonの読み込みに失敗しました: {e}"
        )

        return []


# ============================================================
# news.json保存
# ============================================================

def save_news(news):

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
# RSS記事をnews.json形式へ変換
# ============================================================

def convert_to_news_item(
    item,
    actual_url
):

    return {
        "date": convert_date(
            item["pub_date"]
        ),
        "title": item["title"],
        "source": "コミックナタリー",
        "category": "ニュース",
        "author": "入江亜季",
        "url": actual_url,
        "keyword": "入江亜季, 北北西に曇と往け",
    }


# ============================================================
# 成功した検索結果を確認
# ============================================================

def check_natalie_results(
    success_results
):

    print()
    print("=" * 60)
    print("コミックナタリー記事の確認")
    print("=" * 60)

    checked_results = []

    for data in success_results:

        search_word = data[
            "search_word"
        ]

        results = data[
            "results"
        ]

        print()
        print(
            f"検索ワード: {search_word}"
        )

        for index, item in enumerate(
            results,
            start=1
        ):

            print()
            print(
                f"[記事 {index}]"
            )

            print(
                f"タイトル: "
                f"{item['title']}"
            )

            print(
                f"RSS URL: "
                f"{item['link']}"
            )

            print(
                f"配信元: "
                f"{item['source']}"
            )

            # ------------------------------------------------
            # Google News URLを実際の記事URLへ変換
            # ------------------------------------------------

            actual_url = resolve_google_news_url(
                item["link"]
            )

            if actual_url:

                print(
                    f"実際の記事URL: "
                    f"{actual_url}"
                )

                if is_natalie_url(
                    actual_url
                ):

                    print(
                        "★ コミックナタリー判定: YES"
                    )

                    checked_results.append({
                        "item": item,
                        "actual_url": actual_url,
                    })

                else:

                    print(
                        "→ コミックナタリー判定: NO"
                    )

            else:

                print(
                    "→ 実際の記事URLを"
                    "取得できませんでした。"
                )

            # ------------------------------------------------
            # Google Newsへの連続アクセスを避ける
            # ------------------------------------------------

            time.sleep(
                1
            )

    print()
    print("-" * 60)

    print(
        f"コミックナタリー判定: "
        f"{len(checked_results)}件"
    )

    return checked_results


# ============================================================
# コミックナタリー記事をnews.jsonへ保存
# ============================================================

def save_natalie_results(
    checked_results
):

    print()
    print("=" * 60)
    print("news.jsonへの保存処理")
    print("=" * 60)

    # --------------------------------------------------------
    # 既存データ読み込み
    # --------------------------------------------------------

    news = load_news()

    print(
        f"既存のnews.json: "
        f"{len(news)}件"
    )

    # --------------------------------------------------------
    # 既存URLを取得
    # --------------------------------------------------------

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

    new_items = []

    skipped_count = 0

    # --------------------------------------------------------
    # 新規記事追加
    # --------------------------------------------------------

    for data in checked_results:

        item = data["item"]

        actual_url = data[
            "actual_url"
        ]

        news_item = convert_to_news_item(
            item,
            actual_url
        )

        # ----------------------------------------------------
        # URL重複確認
        # ----------------------------------------------------

        if actual_url in existing_urls:

            skipped_count += 1

            print()
            print(
                "既存記事のためスキップ:"
            )

            print(
                news_item["title"]
            )

            continue

        # ----------------------------------------------------
        # 新規追加
        # ----------------------------------------------------

        news.append(
            news_item
        )

        new_items.append(
            news_item
        )

        existing_urls.add(
            actual_url
        )

        print()
        print(
            "★ 新規記事を追加:"
        )

        print(
            f"タイトル: "
            f"{news_item['title']}"
        )

        print(
            f"日付: "
            f"{news_item['date']}"
        )

        print(
            f"URL: "
            f"{news_item['url']}"
        )

    # --------------------------------------------------------
    # 保存
    # --------------------------------------------------------

    if new_items:

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
            "新しく追加する記事はありません。"
        )

    # --------------------------------------------------------
    # 集計
    # --------------------------------------------------------

    print()
    print("-" * 60)

    print(
        f"新規追加: "
        f"{len(new_items)}件"
    )

    print(
        f"重複スキップ: "
        f"{skipped_count}件"
    )

    print(
        f"news.json合計: "
        f"{len(news)}件"
    )

    return new_items


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print(
        "コミックナタリー"
        " Google News RSS取得テスト"
    )

    print()

    print(
        f"保存先:"
    )

    print(
        NEWS_JSON
    )

    print()

    success_count = 0

    success_results = []

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

            success_results.append({
                "search_word": search_word,
                "results": results,
            })

        except Exception as e:

            print()
            print(
                "RSSの解析中に"
                "エラーが発生しました。"
            )

            print(
                f"エラー: {e}"
            )

        # ----------------------------------------------------
        # 検索ワード間隔
        # ----------------------------------------------------

        if search_word != SEARCH_WORDS[-1]:

            time.sleep(
                3
            )

    # ========================================================
    # RSS取得結果
    # ========================================================

    print()
    print("=" * 60)
    print("RSS取得テスト結果")
    print("=" * 60)

    print(
        f"成功した検索: "
        f"{success_count}/{len(SEARCH_WORDS)}"
    )

    # ========================================================
    # 実際の記事URLを確認
    # ========================================================

    if success_results:

        checked_results = check_natalie_results(
            success_results
        )

    else:

        checked_results = []

        print()
        print(
            "成功したRSS検索がないため、"
            "記事URLの確認を行いません。"
        )

    # ========================================================
    # news.jsonへ保存
    # ========================================================

    if checked_results:

        new_items = save_natalie_results(
            checked_results
        )

    else:

        new_items = []

        print()
        print(
            "コミックナタリーの記事が"
            "見つからなかったため、"
            "news.jsonは変更しません。"
        )

    # ========================================================
    # 最終結果
    # ========================================================

    print()
    print("=" * 60)
    print("最終結果")
    print("=" * 60)

    print(
        f"RSS取得成功: "
        f"{success_count}/{len(SEARCH_WORDS)}"
    )

    print(
        f"コミックナタリー記事: "
        f"{len(checked_results)}件"
    )

    print(
        f"news.jsonへ新規追加: "
        f"{len(new_items)}件"
    )

    if success_count == len(
        SEARCH_WORDS
    ):

        print()
        print(
            "すべてのRSS検索に成功しました。"
        )

    elif success_count > 0:

        print()
        print(
            "一部のRSS検索に成功しました。"
        )

    else:

        print()
        print(
            "RSS検索にすべて失敗しました。"
        )

        raise SystemExit(1)