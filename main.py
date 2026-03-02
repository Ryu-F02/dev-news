import os
import json
import feedparser
import requests
from newspaper import Article
from openai import OpenAI
from datetime import datetime, timedelta
from urllib.parse import urlparse

# ==========================
# 環境変数
# ==========================
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================
# RSSソース（4カテゴリ網羅）
# ==========================
RSS_FEEDS = {

    # 新聞系
    "NetworkWorld": "https://www.networkworld.com/category/networking/index.rss",
    "TheRegister": "https://www.theregister.com/security/headlines.atom",
    "ArsTechnica": "https://arstechnica.com/information-technology/feed/",
    "ITmedia": "https://rss.itmedia.co.jp/rss/2.0/enterprise.xml",

    # 日系ブログ
    "IIJ": "https://eng-blog.iij.ad.jp/feed",
    "Sakura": "https://knowledge.sakura.ad.jp/feed/",
    "MilestoneOfSE": "https://milestone-of-se.nesuke.com/feed/",

    # 海外ブログ
    "PacketPushers": "https://packetpushers.net/feed/",
    "ipSpace": "https://blog.ipspace.net/rss.xml",
    "Cloudflare": "https://blog.cloudflare.com/rss/",
    "AWSNetworking": "https://aws.amazon.com/blogs/networking-and-content-delivery/feed/",
    "GoogleCloud": "https://cloud.google.com/blog/rss/",

    # Reddit
    "RedditNetworking": "https://www.reddit.com/r/networking/.rss",
    "RedditNetsec": "https://www.reddit.com/r/netsec/.rss",
    "RedditSysadmin": "https://www.reddit.com/r/sysadmin/.rss",
}

# ==========================
# 本文抽出
# ==========================
def extract_article(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.title, article.text[:5000]
    except:
        return None, None

# ==========================
# AI評価（トレンド特化）
# ==========================
def evaluate_article(title, content, source):

    prompt = f"""
あなたはエンタープライズネットワークアーキテクトです。

目的：
Enterprise Network技術トレンドを検出する。

以下の記事を評価してください。

重視する観点：
- SASE / SD-WAN / Zero Trust
- EVPN / VXLAN / BGP
- DC / マルチクラウド接続
- 大規模障害
- セキュリティ重大脆弱性
- ベンダー戦略変化
- 標準化動向（IETFなど）

低評価：
- 製品宣伝
- 初学者向け基礎解説
- 表面的ニュース

出力はJSONのみ：

{{
  "score": 0-100,
  "category": "",
  "trend_level": "low|medium|high",
  "why": "",
  "learning_points": ["", "", ""]
}}

Source: {source}
Title: {title}
Content: {content}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content


# ==========================
# Discord送信
# ==========================
def send_to_discord(title, link, source, ai_json):

    score = ai_json.get("score", 0)
    category = ai_json.get("category", "")
    trend = ai_json.get("trend_level", "")
    why = ai_json.get("why", "")
    learning = "\n".join([f"- {x}" for x in ai_json.get("learning_points", [])])

    message = f"""
**{title}**
Source: {source}
Score: {score} / 100
Trend: {trend}
Category: {category}

Why:
{why}

Learning Points:
{learning}

Link:
{link}
"""

    payload = {
        "content": message
    }

    requests.post(DISCORD_WEBHOOK, json=payload)


# ==========================
# メイン処理
# ==========================
def main():

    for source_name, feed_url in RSS_FEEDS.items():

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:

            # 48時間以内の記事のみ
            if hasattr(entry, "published_parsed"):
                pub_date = datetime(*entry.published_parsed[:6])
                if pub_date < datetime.now() - timedelta(days=2):
                    continue

            link = entry.link
            title, content = extract_article(link)

            if not content:
                continue

            ai_raw = evaluate_article(title, content, source_name)

            try:
                ai_json = json.loads(ai_raw)
            except:
                continue

            # スコア閾値
            if ai_json.get("score", 0) >= 75:
                send_to_discord(title, link, source_name, ai_json)


if __name__ == "__main__":
    main()
