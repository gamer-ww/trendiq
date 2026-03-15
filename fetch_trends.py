import os
import json
import requests
from datetime import datetime, timedelta
from pytrends.request import TrendReq
import google.generativeai as genai
from supabase import create_client

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
YOUTUBE_KEY = os.environ['YOUTUBE_API_KEY']
NEWS_KEY = os.environ['NEWS_API_KEY']
GEMINI_KEY = os.environ['GEMINI_API_KEY']
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)

TOPICS = [
    {"query": "LPG gas price India", "category": "incidents", "hashtag": "lpgpricehike"},
    {"query": "RBI interest rate India", "category": "finance", "hashtag": "rbipolicy"},
    {"query": "Bitcoin India price", "category": "finance", "hashtag": "bitcoinindia"},
    {"query": "AI India technology", "category": "tech", "hashtag": "aiindia"},
    {"query": "India Pakistan geopolitics", "category": "incidents", "hashtag": "indiapakistan"},
    {"query": "Sensex Nifty stock market", "category": "finance", "hashtag": "stockmarket"},
    {"query": "India startup funding 2025", "category": "startups", "hashtag": "startupindia"},
    {"query": "BRICS India geopolitics", "category": "politics", "hashtag": "brics"},
    {"query": "India economy GDP", "category": "business", "hashtag": "indianeconomy"},
    {"query": "petrol diesel price India", "category": "incidents", "hashtag": "petrolindia"},
]


def fetch_youtube(topic_query):
    print(f"  YouTube: {topic_query}")
    since = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet", "q": topic_query, "type": "video",
        "order": "viewCount", "publishedAfter": since,
        "regionCode": "IN", "maxResults": 10, "key": YOUTUBE_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        items = data.get('items', [])
        return {"video_count": len(items), "top_title": items[0]['snippet']['title'] if items else ""}
    except Exception as e:
        print(f"    YouTube error: {e}")
        return {"video_count": 0, "top_title": ""}


def fetch_google_trends(topic_query):
    print(f"  Google Trends: {topic_query}")
    try:
        pt = TrendReq(hl='en-IN', tz=330, timeout=(10, 25))
        pt.build_payload([topic_query], timeframe='now 1-d', geo='IN')
        df = pt.interest_over_time()
        if not df.empty and topic_query in df.columns:
            return int(df[topic_query].mean())
    except Exception as e:
        print(f"    Trends error: {e}")
    return 50


def fetch_news(topic_query):
    print(f"  News: {topic_query}")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": topic_query, "language": "en",
        "sortBy": "publishedAt", "pageSize": 5, "apiKey": NEWS_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        articles = r.json().get('articles', [])
        sources = list(set([a['source']['name'] for a in articles[:3]]))
        return {"count": len(articles), "sources": sources}
    except Exception as e:
        print(f"    News error: {e}")
        return {"count": 0, "sources": []}


def fetch_instagram(hashtag):
    return {"reel_count": 0, "views": 0}


def analyze_with_gemini(all_data):
    print("Gemini AI analysis ho rahi hai...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
You are an AI content strategy assistant for Indian YouTube creators.
Here is trending data from India: {json.dumps(all_data[:5], ensure_ascii=False)}

Return ONLY valid JSON, no markdown, no explanation:
{{
  "topics": [
    {{
      "title": "topic in Hinglish",
      "category": "tech",
      "trend_score": 85,
      "fact_status": "verified",
      "youtube_videos": "45K",
      "youtube_views": "890M",
      "ig_hashtag": "#example",
      "ig_reels": "8K",
      "ig_views": "980K",
      "cross_platform": true,
      "since": "2 din se",
      "sources": "Times of India",
      "yt_score": 85,
      "ig_score": 74
    }}
  ],
  "recommendations": [
    {{
      "title": "Video idea in Hinglish",
      "score": 93,
      "reason": "reason in Hinglish",
      "platform": "both"
    }}
  ],
  "trending_audios": [],
  "stats": {{
    "total_topics": 5,
    "verified_count": 3,
    "total_views": "2B",
    "top_category": "Finance"
  }}
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini error: {e}")
        return {}


def save_to_supabase(analysis):
    print("Supabase mein save ho raha hai...")
    record = {
        "fetched_at": datetime.utcnow().isoformat(),
        "topics": analysis.get('topics', []),
        "recommendations": analysis.get('recommendations', []),
        "trending_audios": analysis.get('trending_audios', []),
        "stats": analysis.get('stats', {})
    }
    supabase.table('trendiq_data').insert(record).execute()
    print("Save ho gaya!")


def main():
    print("=" * 50)
    print(f"TrendIQ Start: {datetime.utcnow()}")
    print("=" * 50)

    all_raw_data = []

    for topic in TOPICS:
        print(f"\nTopic: {topic['query']}")
        yt_data = fetch_youtube(topic['query'])
        gt_score = fetch_google_trends(topic['query'])
        news_data = fetch_news(topic['query'])
        ig_data = fetch_instagram(topic['hashtag'])

        all_raw_data.append({
            "topic": topic['query'],
            "category": topic['category'],
            "hashtag": topic['hashtag'],
            "google_score": gt_score,
            "yt_videos": yt_data['video_count'],
            "yt_top_title": yt_data['top_title'],
            "news_count": news_data['count'],
            "news_sources": news_data['sources'],
            "ig_reels": ig_data['reel_count'],
            "ig_views": ig_data['views'],
        })

    analysis = analyze_with_gemini(all_raw_data)

    if not analysis.get('topics'):
        print("Gemini quota hit — raw data save kar raha hai")
        analysis = {
            "topics": [
                {
                    "title": t["topic"],
                    "category": t["category"],
                    "trend_score": t["google_score"],
                    "fact_status": "partial",
                    "youtube_videos": str(t["yt_videos"]) + " videos",
                    "youtube_views": "N/A",
                    "ig_hashtag": "#" + t["hashtag"],
                    "ig_reels": "0",
                    "ig_views": "0",
                    "cross_platform": False,
                    "since": "aaj",
                    "sources": ", ".join(t["news_sources"]) if t["news_sources"] else "N/A",
                    "yt_score": t["google_score"],
                    "ig_score": 0
                }
                for t in all_raw_data
            ],
            "recommendations": [
                {
                    "title": all_raw_data[0]["topic"] + " pe video banao",
                    "score": all_raw_data[0]["google_score"],
                    "reason": "Abhi sabse zyada trending hai",
                    "platform": "youtube"
                }
            ],
            "trending_audios": [],
            "stats": {
                "total_topics": len(all_raw_data),
                "verified_count": 0,
                "total_views": "N/A",
                "top_category": "Mixed"
            }
        }

    save_to_supabase(analysis)

    print("\n" + "=" * 50)
    print("TrendIQ Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
