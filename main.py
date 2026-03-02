import os
import json
import feedparser
import requests
from openai import OpenAI
from datetime import datetime, timedelta

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

RSS_FEEDS = {
    "NetworkWorld": "https://www.networkworld.com/category/networking/index.rss",
    "TheRegister": "https://www.theregister.com/security/headlines.atom",
    "ArsTechnica": "https://arstechnica.com/information-technology/feed/",
    "ITmedia": "https://rss.itmedia.co.jp/rss/2.0/enterprise.xml",
    "IIJ": "https://eng-blog.iij.ad.jp/feed",
    "Sakura": "https://knowledge.sakura.ad.jp/feed/",
    "MilestoneOfSE": "https://milestone-of-se.nesuke.com/feed/",
    "PacketPushers": "https://packetpushers.net/feed/",
    "ipSpace": "https://blog.ipspace.net/rss.xml",
    "Cloudflare": "https://blog.cloudflare.com/rss/",
    "AWSNetworking": "https://aws.amazon.com/blogs/networking-and-content-delivery/feed/",
    "GoogleCloud": "https://cloud.google.com/blog/rss/",
    "RedditNetworking": "https://www.reddit.com/r/networking/.rss",
    "RedditNetsec": "https://www.reddit.com/r/netsec/.rss",
    "RedditSysadmin": "https://www.reddit.com/r/sysadmin/.rss",
}

def evaluate_article(title, summary, source):

    prompt = f"""
あなたはエンタープライズネットワークアーキテクトです。
Enterprise NW技術トレンドとして重要か評価してください。

重視：
- SASE / SD-WAN / Zero Trust
- EVPN / VXLAN / BGP
- DC / クラウド接続
- 重大セキュリティ脆弱性
- ベンダー戦略変化

JSONのみで出力：

{{
 "score": 0-100,
 "category": "",
 "trend_level": "low|medium|high",
 "why": "",
 "learning_points": ["", "", ""]
}}

Source: {source}
Title: {title}
Summary: {summary}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content


def send_to_discord(title, link, source, ai_json):

    message = f"""
**{title}**
Source: {source}
Score: {ai_json.get('score')}
Trend: {ai_json.get('trend_level')}
Category: {ai_json.get('category')}

Why:
{ai_json.get('why')}

Learning:
- {"\n- ".join(ai_json.get('learning_points', []))}

{link}
"""

    requests.post(DISCORD_WEBHOOK, json={"content": message})


def main():

    for source_name, feed_url in RSS_FEEDS.items():
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:

            if hasattr(entry, "published_parsed"):
                pub_date = datetime(*entry.published_parsed[:6])
                if pub_date < datetime.now() - timedelta(days=2):
                    continue

            title = entry.title
            summary = entry.get("summary", "")
            link = entry.link

            ai_raw = evaluate_article(title, summary, source_name)

            try:
                ai_json = json.loads(ai_raw)
            except:
                continue

            if ai_json.get("score", 0) >= 75:
                send_to_discord(title, link, source_name, ai_json)


if __name__ == "__main__":
    main()
