import time
from urllib.parse import quote

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
    print("=" * 70)
    print("Google News RSSへアクセス")
    print("=" * 70)

    print(
        f"検索ワード: {search_word}"
    )

    print(
        f"RSS URL: {url}"
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
# RSSの内容をデバッグ表示
# ============================================================

def debug_rss(response):

    soup = BeautifulSoup(
        response.content,
        "xml"
    )

    items = soup.find_all(
        "item"
    )

    print()
    print("=" * 70)
    print(
        f"RSS内の記事数: {len(items)}件"
    )
    print("=" * 70)

    if not items:

        print(
            "RSS内にitemがありません。"
        )

        return

    # --------------------------------------------------------
    # 最初の3件を詳しく表示
    # --------------------------------------------------------

    for index, item in enumerate(
        items[:3],
        start=1
    ):

        print()
        print("=" * 70)
        print(
            f"【RSS記事 {index}件目】"
        )
        print("=" * 70)

        # ----------------------------------------------------
        # title
        # ----------------------------------------------------

        title = item.find(
            "title"
        )

        print()
        print(
            "[title]"
        )

        if title:

            print(
                title.get_text(
                    strip=True
                )
            )

        else:

            print(
                "なし"
            )

        # ----------------------------------------------------
        # link
        # ----------------------------------------------------

        link = item.find(
            "link"
        )

        print()
        print(
            "[link]"
        )

        if link:

            print(
                link.get_text(
                    strip=True
                )
            )

        else:

            print(
                "なし"
            )

        # ----------------------------------------------------
        # source
        # ----------------------------------------------------

        source = item.find(
            "source"
        )

        print()
        print(
            "[source]"
        )

        if source:

            print(
                source.get_text(
                    strip=True
                )
            )

            print(
                f"source属性: "
                f"{source.attrs}"
            )

        else:

            print(
                "なし"
            )

        # ----------------------------------------------------
        # pubDate
        # ----------------------------------------------------

        pub_date = item.find(
            "pubDate"
        )

        print()
        print(
            "[pubDate]"
        )

        if pub_date:

            print(
                pub_date.get_text(
                    strip=True
                )
            )

        else:

            print(
                "なし"
            )

        # ----------------------------------------------------
        # description
        # ----------------------------------------------------

        description = item.find(
            "description"
        )

        print()
        print(
            "[description]"
        )

        if description:

            print(
                description.get_text(
                    strip=True
                )
            )

        else:

            print(
                "なし"
            )

        # ----------------------------------------------------
        # その他のタグ
        # ----------------------------------------------------

        print()
        print(
            "[その他のRSSデータ]"
        )

        for child in item.find_all(
            recursive=False
        ):

            print(
                f"タグ: <{child.name}>"
            )

            print(
                f"内容: "
                f"{child.get_text(strip=True)}"
            )

            if child.attrs:

                print(
                    f"属性: "
                    f"{child.attrs}"
                )

            print()

        # ----------------------------------------------------
        # XMLそのもの
        # ----------------------------------------------------

        print()
        print(
            "[item全体のXML]"
        )

        print(
            item.prettify()
        )


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "コミックナタリー"
        " Google News RSSデバッグテスト"
    )

    print()
    print(
        "※今回はnews.jsonを変更しません。"
    )

    print()

    success_count = 0

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

            debug_rss(
                response
            )

            success_count += 1

        except Exception as e:

            print()
            print(
                "RSS解析中に"
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
    # 結果
    # ========================================================

    print()
    print("=" * 70)
    print("テスト結果")
    print("=" * 70)

    print(
        f"RSS取得成功: "
        f"{success_count}/{len(SEARCH_WORDS)}"
    )

    print()

    print(
        "上記のRSSデータを確認してください。"
    )

    print(
        "特に [link]、[source]、"
        "[description] の内容が重要です。"
    )
