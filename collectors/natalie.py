import json
import os
import time
from datetime import datetime, timezone
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

# news.json
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

            # ------------------------------------------------
            # 成功
            # ------------------------------------------------

            if response.status_code == 200:

                print(
                    "RSSの取得に成功しました。"
                )

                return response

            # ------------------------------------------------
            # エラー
            # ------------------------------------------------

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
# URL確認
# ============================================================

def is_natalie_url(url):

    if not url:
        return False

    parsed = urlparse(
        url
    )

    hostname = (
        parsed.hostname or ""
    ).lower()

    return (
        hostname == "natalie.mu"
        or hostname.endswith(
            ".natalie.mu"
        )
    )


# ============================================================
# RSS日時をYYYY-MM-DDに変換
# ============================================================

def convert_date(pub_date):

    if not pub_date:

        return ""

    try:

        dt = datetime.strptime(
            pub_date,
            "%a, %d %b %Y %H:%M:%S %Z"
        )

        return dt.strftime(
            "%Y-%m-%d"
        )

    except ValueError:

        pass

    try:

        dt = datetime.strptime(
            pub_date,
            "%a, %d %b %Y %H:%M:%S %z"
        )

        return dt.astimezone(
            timezone.utc
        ).strftime(
            "%Y-%m-%d"
        )

    except ValueError:

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
# コミックナタリーの記事だけをnews.json形式へ変換
# ============================================================

def convert_to_news_item(item):

    return {
        "date": convert_date(
            item["pub_date"]
        ),
        "title": item["title"],
        "source": "コミックナタリー",
        "category": "ニュース",
        "author": "入江亜季",
        "url": item["link"],
        "keyword": "入江亜季, 北北西に曇と往け",
    }


# ============================================================
# コミックナタリーの記事をnews.jsonへ追加
# ============================================================

def save_natalie_results(
    success_results
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
        f"既存のnews.json: {len(news)}件"
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

    # --------------------------------------------------------
    # 新規記事を追加
    # --------------------------------------------------------

    new_items = []

    skipped_count = 0

    for data in success_results:

        results = data["results"]

        for item in results:

            # コミックナタリー以外は除外
            if not is_natalie_url(
                item["link"]
            ):

                continue

            news_item = convert_to_news_item(
                item
            )

            url = news_item["url"]

            # URLが空なら除外
            if not url:

                continue

            # 既に存在する記事
            if url in existing_urls:

                skipped_count += 1

                print()
                print(
                    "既存記事のためスキップ:"
                )

                print(
                    news_item["title"]
                )

                continue

            # 新規記事
            news.append(
                news_item
            )

            new_items.append(
                news_item
            )

            existing_urls.add(
                url
            )

            print()
            print(
                "★ 新規記事:"
            )

            print(
                f"タイトル: {news_item['title']}"
            )

            print(
                f"日付: {news_item['date']}"
            )

            print(
                f"URL: {news_item['url']}"
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
            f"news.jsonを更新しました。"
        )

    else:

        print()
        print(
            "新しく追加する記事はありません。"
        )

    # --------------------------------------------------------
    # 結果
    # --------------------------------------------------------

    print()
    print("-" * 60)

    print(
        f"新規追加: {len(new_items)}件"
    )

    print(
        f"重複スキップ: {skipped_count}件"
    )

    print(
        f"news.json合計: {len(news)}件"
    )

    return new_items


# ============================================================
# 取得したコミックナタリー記事を表示
# ============================================================

def show_results(
    search_word,
    results
):

    print()
    print("=" * 60)
    print(
        f"検索結果: {search_word}"
    )
    print("=" * 60)

    if not results:

        print(
            "記事が見つかりませんでした。"
        )

        return

    natalie_count = 0

    for index, item in enumerate(
        results,
        start=1
    ):

        title = item["title"]
        link = item["link"]
        pub_date = item["pub_date"]
        source = item["source"]

        natalie = is_natalie_url(
            link
        )

        if natalie:

            natalie_count += 1

        print()
        print(
            f"[{index}]"
        )

        print(
            f"タイトル: {title}"
        )

        print(
            f"公開日時: {pub_date}"
        )

        print(
            f"配信元: {source}"
        )

        print(
            f"URL: {link}"
        )

        if natalie:

            print(
                "★ コミックナタリーの記事です"
            )

        else:

            print(
                "→ コミックナタリー以外"
            )

    print()
    print(
        "-" * 60
    )

    print(
        f"Google News取得件数: "
        f"{len(results)}件"
    )

    print(
        f"コミックナタリー判定: "
        f"{natalie_count}件"
    )


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
        f"保存先: {NEWS_JSON}"
    )

    print()

    success_count = 0

    # 成功した検索と取得内容
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
                f"取得失敗: {search_word}"
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

            show_results(
                search_word,
                results
            )

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
    # テスト結果
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
    # 成功した検索があれば保存
    # ========================================================

    if success_results:

        new_items = save_natalie_results(
            success_results
        )

    else:

        new_items = []

        print()
        print(
            "成功した検索がないため、"
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