import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

URL = "https://natalie.mu/comic/artist/2343"

MAX_RETRIES = 3

WAIT_TIMES = [
    10,
    30,
    60
]

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
# 著者ページ取得
# ============================================================

def get_artist_page():

    for attempt in range(MAX_RETRIES):

        print(
            f"コミックナタリー著者ページへアクセス中..."
            f"（試行 {attempt + 1}/{MAX_RETRIES}）"
        )

        try:

            response = requests.get(
                URL,
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

                print()
                print(
                    "著者ページの取得に成功しました。"
                )

                return response

            # ------------------------------------------------
            # 405
            # ------------------------------------------------

            if response.status_code == 405:

                print(
                    "405 Method Not Allowed"
                )

                if attempt < MAX_RETRIES - 1:

                    wait_time = WAIT_TIMES[attempt]

                    print(
                        f"{wait_time}秒待って再試行します..."
                    )

                    import time
                    time.sleep(wait_time)

                    continue

                print(
                    "405エラーのため取得を中止します。"
                )

                return None

            # ------------------------------------------------
            # 403
            # ------------------------------------------------

            if response.status_code == 403:

                print(
                    "403 Forbidden"
                )

                if attempt < MAX_RETRIES - 1:

                    wait_time = WAIT_TIMES[attempt]

                    print(
                        f"{wait_time}秒待って再試行します..."
                    )

                    import time
                    time.sleep(wait_time)

                    continue

                print(
                    "403エラーのため取得を中止します。"
                )

                return None

            # ------------------------------------------------
            # その他
            # ------------------------------------------------

            print(
                f"予期しないHTTPステータス: "
                f"{response.status_code}"
            )

            return None

        except requests.RequestException as e:

            print(
                f"通信エラー: {e}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = WAIT_TIMES[attempt]

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                import time
                time.sleep(wait_time)

                continue

            return None

    return None


# ============================================================
# ページ内容確認
# ============================================================

def check_page(response):

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    print()
    print("=" * 60)
    print("ページ内容を確認します")
    print("=" * 60)

    # --------------------------------------------------------
    # title
    # --------------------------------------------------------

    title = soup.find("title")

    if title:

        print()
        print(
            "ページタイトル:"
        )

        print(
            title.get_text(
                " ",
                strip=True
            )
        )

    # --------------------------------------------------------
    # h1
    # --------------------------------------------------------

    h1 = soup.find("h1")

    if h1:

        print()
        print(
            "h1:"
        )

        print(
            h1.get_text(
                " ",
                strip=True
            )
        )

    # --------------------------------------------------------
    # 「入江亜季のニュース」を探す
    # --------------------------------------------------------

    page_text = soup.get_text(
        " ",
        strip=True
    )

    if "入江亜季のニュース" in page_text:

        print()
        print(
            "「入江亜季のニュース」を確認できました。"
        )

    else:

        print()
        print(
            "「入江亜季のニュース」が"
            "見つかりませんでした。"
        )

    # --------------------------------------------------------
    # ページサイズ
    # --------------------------------------------------------

    print()
    print(
        f"取得したHTMLサイズ: "
        f"{len(response.text):,} bytes"
    )

    # --------------------------------------------------------
    # ニュース記事URLを確認
    # --------------------------------------------------------

    news_links = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/comic/news/" not in href:
            continue

        text = link.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        news_links.append(
            (
                text,
                href
            )
        )

    # URL重複削除

    unique_links = []

    seen_urls = set()

    for text, href in news_links:

        if href in seen_urls:
            continue

        seen_urls.add(href)

        unique_links.append(
            (
                text,
                href
            )
        )

    print()
    print(
        f"著者ページ内で確認できた"
        f"ニュースURL: {len(unique_links)}件"
    )

    # --------------------------------------------------------
    # 最初の10件だけ表示
    # --------------------------------------------------------

    if unique_links:

        print()
        print(
            "【ニュースURL確認】"
        )

        print()

        for index, (text, href) in enumerate(
            unique_links[:10],
            start=1
        ):

            print(
                f"{index}. {text}"
            )

            print(
                f"   {href}"
            )

    print()
    print("=" * 60)
    print(
        "著者ページの確認が完了しました。"
    )
    print("=" * 60)


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print(
        "コミックナタリー著者ページ"
        "取得テストを開始します。"
    )

    print()

    print(
        f"取得URL:"
    )

    print(
        URL
    )

    print()

    try:

        response = get_artist_page()

        if response is None:

            print()
            print(
                "著者ページを取得できませんでした。"
            )

            raise SystemExit(1)

        check_page(response)

        print()
        print(
            "テスト成功"
        )

    except Exception as e:

        print()
        print(
            "テスト中にエラーが発生しました。"
        )

        print(
            f"エラー: {e}"
        )

        raise SystemExit(1)