import os
import json
import feedparser
import requests
from openai import OpenAI
from datetime import datetime, timedelta

def main():
    requests.post(DISCORD_WEBHOOK, json={"content": "🚀 bot test message"})

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

RSS_FEEDS = {
    "NetworkWorld": "https://www.networkworld.com/category/networking/index.rss",
    "RedditNetworking": "https://www.reddit.com/r/networking/.rss"
}

def evaluate_article(title, summary, source):

    prompt = f"""
あなたはエンタープライズネットワーク専門アナリストです。

以下の記事が企業ネットワーク（SD-WAN、SASE、BGP、DC、セキュリティ、Cisco、Juniper等）
の観点でどれほど重要か評価してください。

【必須条件】
・whyは必ず日本語で書く
・簡潔に2〜3文
・JSONのみ出力

出力形式：
{{
 "score": 0-100,
 "why": "日本語で理由を書く"
}}

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

Why:
{ai_json.get('why')}

{link}
"""

    requests.post(DISCORD_WEBHOOK, json={"content": message})


def main():

    for source_name, feed_url in RSS_FEEDS.items():
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:3]:

            title = entry.title
            summary = entry.get("summary", "")
            link = entry.link

            ai_raw = evaluate_article(title, summary, source_name)

            try:
                ai_json = json.loads(ai_raw)
            except:
                continue

            if ai_json.get("score", 0) >= 70:
                send_to_discord(title, link, source_name, ai_json)


if __name__ == "__main__":
    main()
