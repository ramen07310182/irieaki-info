import json
import os
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
# 保存対象タイトル
#
# タイトルに以下のどちらかが含まれている記事だけ保存する
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
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


# ============================================================
# タイトルフィルタ
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

    encoded_word = quote(search_word)

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

            print(
                f"HTTPエラー: "
                f"{response.status_code}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = WAIT_TIMES[attempt]

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(wait_time)

        except requests.RequestException as e:

            print(
                f"通信エラー: {e}"
            )

            if attempt < MAX_RETRIES - 1:

                wait_time = WAIT_TIMES[attempt]

                print(
                    f"{wait_time}秒待って再試行します..."
                )

                time.sleep(wait_time)

    return None


# ============================================================
# RSS解析
# ============================================================

def parse_rss(response):

    soup = BeautifulSoup(
        response.content,
        "xml",
    )

    items = soup.find_all("item")

    print()
    print(
        f"RSS内の記事数: {len(items)}件"
    )

    results = []

    for item in items:

        title_element = item.find("title")
        link_element = item.find("link")
        pub_date_element = item.find("pubDate")
        source_element = item.find("source")

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
# natalie.mu URL判定
# ============================================================

def is_natalie_comic_url(url):

    if not url:
        return False

    try:

        parsed = urlparse(url)

        hostname = (
            parsed.hostname or ""
        ).lower()

        path = (
            parsed.path or ""
        ).lower()

        return (
            hostname == "natalie.mu"
            and path.startswith("/comic/")
        )

    except Exception:

        return False


# ============================================================
# Google News URLから元記事URLを取得
#
# 現在のGoogle News CBMi...形式対応
#
# 1. Google News記事ページをGET
# 2. c-wiz[data-p] を取得
# 3. garturlreqデータを取り出す
# 4. batchexecuteへFbv4jeをPOST
# 5. garturlresから元記事URLを取得
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
    # Google News記事ページを取得
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
    # c-wiz[data-p] を探す
    # --------------------------------------------------------

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    c_wiz = soup.select_one(
        "c-wiz[data-p]"
    )

    if c_wiz is None:

        print(
            "c-wiz[data-p] が見つかりません。"
        )

        return ""

    data_p = c_wiz.get(
        "data-p"
    )

    if not data_p:

        print(
            "data-pが空です。"
        )

        return ""

    # --------------------------------------------------------
    # data-pからgarturlreqを作成
    # --------------------------------------------------------

    try:

        json_text = data_p.replace(
            "%.@.",
            '["garturlreq",'
        )

        obj = json.loads(
            json_text
        )

    except Exception as e:

        print(
            f"data-p解析エラー: {e}"
        )

        return ""

    # --------------------------------------------------------
    # Google内部RPC用データ
    # --------------------------------------------------------

    try:

        request_data = [
            [
                [
                    "Fbv4je",
                    json.dumps(
                        obj[:-6] + obj[-2:],
                        separators=(
                            ",",
                            ":"
                        ),
                    ),
                    "null",
                    "generic",
                ]
            ]
        ]

        payload = {
            "f.req": json.dumps(
                request_data,
                separators=(
                    ",",
                    ":"
                ),
            )
        }

    except Exception as e:

        print(
            f"RPCデータ作成エラー: {e}"
        )

        return ""

    # --------------------------------------------------------
    # batchexecute
    # --------------------------------------------------------

    batchexecute_url = (
        "https://news.google.com/"
        "_/DotsSplashUi/data/batchexecute"
    )

    rpc_headers = {
        "Content-Type": (
            "application/x-www-form-urlencoded;"
            "charset=UTF-8"
        ),
        "User-Agent": HEADERS["User-Agent"],
        "Referer": "https://news.google.com/",
    }

    try:

        rpc_response = session.post(
            batchexecute_url,
            headers=rpc_headers,
            data=payload,
            timeout=30,
        )

    except requests.RequestException as e:

        print(
            f"batchexecute通信エラー: {e}"
        )

        return ""

    print(
        f"batchexecute: "
        f"HTTP {rpc_response.status_code}"
    )

    if rpc_response.status_code != 200:

        return ""

    text = rpc_response.text

    # --------------------------------------------------------
    # garturlresを検索
    # --------------------------------------------------------

    marker = (
        '[\\"garturlres\\",\\"'
    )

    start = text.find(
        marker
    )

    if start == -1:

        marker = (
            '["garturlres","'
        )

        start = text.find(
            marker
        )

        if start == -1:

            print(
                "garturlresが見つかりません。"
            )

            return ""

    start += len(marker)

    # --------------------------------------------------------
    # URL終了位置
    # --------------------------------------------------------

    end = text.find(
        '",',
        start
    )

    if end == -1:

        print(
            "garturlresの終了位置を"
            "特定できませんでした。"
        )

        return ""

    article_url = text[
        start:end
    ]

    # --------------------------------------------------------
    # エスケープ解除
    # --------------------------------------------------------

    article_url = (
        article_url
        .replace('\\"', '"')
        .replace("\\/", "/")
        .replace("\\u003d", "=")
        .replace("\\u0026", "&")
    )

    print(
        f"取得した元記事URL: "
        f"{article_url}"
    )

    return article_url


# ============================================================
# RSS日時をYYYY-MM-DDへ変換
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

            data = json.load(f)

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

        f.write("\n")


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
        " Google News RSS取得テスト"
    )
    print("=" * 70)

    print()
    print(
        f"保存先: {NEWS_JSON}"
    )

    # --------------------------------------------------------
    # news.json読み込み
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
            existing_urls.add(url)

    # --------------------------------------------------------
    # RSS取得
    # --------------------------------------------------------

    success_count = 0
    natalie_candidates = []

    checked_google_urls = set()

    # タイトル条件で除外した件数
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
            # ナタリーだけ抽出
            # ------------------------------------------------

            for item in results:

                if not is_natalie_source(
                    item
                ):
                    continue

                # ------------------------------------------------
                # ★ タイトルフィルタ
                #
                # 「入江亜季」
                # または
                # 「北北西に曇と往け」
                # がタイトルに含まれる記事だけ通す
                # ------------------------------------------------

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

                # 同じGoogle News URLは1回だけ
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
                    "★ タイトル条件通過"
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

            time.sleep(3)

    # ========================================================
    # 結果表示
    # ========================================================

    print()
    print("=" * 70)
    print("RSS検索結果")
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
        f"タイトル条件で除外: "
        f"{title_excluded_count}件"
    )

    # ========================================================
    # 元記事URL取得
    # ========================================================

    resolved_results = []

    print()
    print("=" * 70)
    print("Google News → コミックナタリーURL変換")
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

        print(
            f"公開日時: "
            f"{item['pub_date']}"
        )

        # ----------------------------------------------------
        # Google News URL
        # ----------------------------------------------------

        google_news_url = item[
            "link"
        ]

        article_url = resolve_google_news_url(
            google_news_url
        )

        # ----------------------------------------------------
        # ナタリー記事か確認
        # ----------------------------------------------------

        if not article_url:

            print(
                "→ 元記事URL取得失敗"
            )

            continue

        if not is_natalie_comic_url(
            article_url
        ):

            print(
                "→ コミックナタリーURLではないため"
                "スキップ"
            )

            print(
                f"取得URL: {article_url}"
            )

            continue

        print(
            "★ コミックナタリー記事として確定"
        )

        # ----------------------------------------------------
        # 既存URLチェック
        # ----------------------------------------------------

        if article_url in existing_urls:

            print(
                "→ news.jsonに既に存在するためスキップ"
            )

            continue

        resolved_results.append({
            "item": item,
            "article_url": article_url,
        })

        # Googleへの連続アクセスを抑える
        time.sleep(1)

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
        f"ナタリー候補: "
        f"{len(natalie_candidates)}件"
    )

    print(
        f"タイトル条件で除外: "
        f"{title_excluded_count}件"
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