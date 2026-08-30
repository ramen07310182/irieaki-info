import time
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
            # 403
            # ------------------------------------------------

            if response.status_code == 403:

                print(
                    "403 Forbidden"
                )

            # ------------------------------------------------
            # 429
            # ------------------------------------------------

            elif response.status_code == 429:

                print(
                    "429 Too Many Requests"
                )

            # ------------------------------------------------
            # その他
            # ------------------------------------------------

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
# 検索結果表示
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
            "RSSは取得できましたが、"
            "記事がありませんでした。"
        )

        return 0

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

    return natalie_count


# ============================================================
# 成功した検索の内容をまとめて表示
# ============================================================

def show_success_results(
    success_results
):

    print()
    print()
    print("=" * 70)
    print("成功した検索の実際の取得内容")
    print("=" * 70)

    if not success_results:

        print(
            "成功した検索はありません。"
        )

        return

    total_articles = 0
    total_natalie = 0

    for data in success_results:

        search_word = data["search_word"]
        results = data["results"]

        print()
        print(
            "#" * 70
        )

        print(
            f"検索ワード: {search_word}"
        )

        print(
            f"取得記事数: {len(results)}件"
        )

        print(
            "#" * 70
        )

        total_articles += len(
            results
        )

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
                total_natalie += 1

            print()
            print(
                f"【記事 {index}】"
            )

            print(
                f"タイトル : {title}"
            )

            print(
                f"公開日時 : {pub_date}"
            )

            print(
                f"配信元   : {source}"
            )

            print(
                f"URL      : {link}"
            )

            print(
                f"判定     : "
                f"{'コミックナタリー' if natalie else 'その他'}"
            )

    print()
    print("=" * 70)
    print("取得内容の集計")
    print("=" * 70)

    print(
        f"成功した検索数: "
        f"{len(success_results)}件"
    )

    print(
        f"取得した記事総数: "
        f"{total_articles}件"
    )

    print(
        f"コミックナタリー記事: "
        f"{total_natalie}件"
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
        "今回はnews.jsonには保存しません。"
    )

    print()

    success_count = 0

    # 成功した検索と取得内容を保存
    success_results = []

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

            # ------------------------------------------------
            # この検索はRSS取得成功
            # ------------------------------------------------

            success_count += 1

            # 成功した検索の内容を保存
            success_results.append({
                "search_word": search_word,
                "results": results,
            })

            # その場でも表示
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
    # 最後に成功した検索の内容をまとめて表示
    # ========================================================

    show_success_results(
        success_results
    )

    # ========================================================
    # テスト結果
    # ========================================================

    print()
    print("=" * 60)
    print("テスト結果")
    print("=" * 60)

    print(
        f"成功した検索: "
        f"{success_count}/{len(SEARCH_WORDS)}"
    )

    if success_count == len(
        SEARCH_WORDS
    ):

        print()
        print(
            "Google News RSSの"
            "取得テストに成功しました。"
        )

        print()
        print(
            "上に表示された内容が、"
            "今回RSSから実際に取得した記事データです。"
        )

        print()
        print(
            "次の段階で、"
            "この取得データから必要な記事だけを"
            "news.jsonへ保存できます。"
        )

    elif success_count > 0:

        print()
        print(
            "一部の検索に成功しました。"
        )

        print(
            "成功した検索については、"
            "実際に取得した記事内容を上に表示しています。"
        )

    else:

        print()
        print(
            "一部または全部の検索に失敗しました。"
        )

        raise SystemExit(1)
