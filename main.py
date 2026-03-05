import feedparser
import json
import os
import requests
from openai import OpenAI

# ------------------------------
# RSSフィード定義（Enterprise NW寄りのみ）
# ------------------------------
RSS_FEEDS = {
    "NetworkWorld": "https://www.networkworld.com/category/networking/index.rss",
    "ArsTechnica": "https://arstechnica.com/information-technology/feed/",
    "TheRegister": "https://www.theregister.com/security/headlines.atom",
    "Cloudflare": "https://blog.cloudflare.com/rss/",
    "AWSNetworking": "https://aws.amazon.com/blogs/networking-and-content-delivery/feed/",
    "GoogleCloud": "https://cloud.google.com/blog/rss/"
    "Qiita"："https://qiita.com/tags/network/feed"
    "Zenn"："https://zenn.dev/topics/network/feed"
}

# ------------------------------
# Discord送信関数
# ------------------------------
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

def send_to_discord(title, link, source, ai_info):
    message = f"**{title}**\nSource: {source}\nScore: {ai_info.get('score', 'N/A')}\n\n{ai_info.get('why','')}\n{link}"
    payload = {"content": message}
    r = requests.post(DISCORD_WEBHOOK, json=payload)
    if r.status_code != 204:
        print(f"Discord送信失敗: {r.status_code}, {r.text}")

# ------------------------------
# AI評価関数（日本語でスコア付与）
# ------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def evaluate_article(title, summary, source_name):
    prompt = f"""
以下の記事について評価してください。
- 記事タイトル: {title}
- 記事概要: {summary}
- 出典: {source_name}

評価ルール:
1. エンタープライズネットワーク戦略や業界トレンドに関連する重要性を0-100のスコアで付与。
2. 「なぜそのスコアか」を日本語で簡潔に説明。
3. 出力はJSON形式で以下の形式で返すこと。
4. 日本語の記事が出力された場合、加点し、必ず、ランキングに乗せること。

{{"score": 数値, "why": "説明文"}}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ------------------------------
# メイン処理
# ------------------------------
def main():
    candidates = []

    for source_name, feed_url in RSS_FEEDS.items():
        feed = feedparser.parse(feed_url)

        # 各フィード最新5件まで
        for entry in feed.entries[:5]:
            title = entry.title
            summary = entry.get("summary", "")
            link = entry.link

            try:
                ai_raw = evaluate_article(title, summary, source_name)
                ai_json = json.loads(ai_raw)
            except Exception as e:
                print(f"AI評価失敗: {e}")
                continue

            candidates.append({
                "title": title,
                "link": link,
                "source": source_name,
                "score": ai_json.get("score", 0),
                "why": ai_json.get("why","")
            })

    # スコア順に並べる
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # 上位3件を必ず投稿
    top3 = candidates[:3]

    for idx, item in enumerate(top3, 1):
        rank_emoji = ["🥇", "🥈", "🥉"][idx-1] if idx <=3 else ""
        send_to_discord(
            f"{rank_emoji} {item['title']}",
            item["link"],
            item["source"],
            {"score": item["score"], "why": item["why"]}
        )

if __name__ == "__main__":
    main()
