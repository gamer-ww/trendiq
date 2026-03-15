import os
import json
import requests
from datetime import datetime, timedelta
from pytrends.request import TrendReq
from supabase import create_client

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
YOUTUBE_KEY = os.environ['YOUTUBE_API_KEY']
NEWS_KEY = os.environ['NEWS_API_KEY']
GROQ_KEY = os.environ['GROQ_API_KEY']

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TOPICS = [
    {"query": "LPG gas price India 2025",       "category": "incidents",  "hashtag": "lpgpricehike"},
    {"query": "RBI interest rate India 2025",   "category": "finance",    "hashtag": "rbipolicy"},
    {"query": "Bitcoin India price 2025",       "category": "finance",    "hashtag": "bitcoinindia"},
    {"query": "AI India technology 2025",       "category": "tech",       "hashtag": "aiindia"},
    {"query": "India Pakistan border 2025",     "category": "incidents",  "hashtag": "indiapakistan"},
    {"query": "Sensex Nifty stock market",      "category": "finance",    "hashtag": "stockmarket"},
    {"query": "India startup funding 2025",     "category": "startups",   "hashtag": "startupindia"},
    {"query": "BRICS India geopolitics 2025",   "category": "politics",   "hashtag": "brics"},
    {"query": "India economy GDP 2025",         "category": "business",   "hashtag": "indianeconomy"},
    {"query": "petrol diesel price India 2025", "category": "incidents",  "hashtag": "petrolindia"},
    {"query": "Modi government policy 2025",    "category": "politics",   "hashtag": "indiagovernment"},
    {"query": "India tech layoffs startups",    "category": "tech",       "hashtag": "techindia"},
]


def fetch_youtube_videos(topic_query):
    print(f"  YouTube videos: {topic_query}")
    since = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet", "q": topic_query, "type": "video",
        "order": "viewCount", "publishedAfter": since,
        "regionCode": "IN", "maxResults": 5, "key": YOUTUBE_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get('items', [])

        video_ids = [i['id']['videoId'] for i in items if 'videoId' in i.get('id', {})]
        views_map = {}
        if video_ids:
            stats_url = "https://www.googleapis.com/youtube/v3/videos"
            stats_params = {
                "part": "statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": YOUTUBE_KEY
            }
            stats_r = requests.get(stats_url, params=stats_params, timeout=10)
            for v in stats_r.json().get('items', []):
                views_map[v['id']] = int(v['statistics'].get('viewCount', 0))

        videos = []
        for item in items:
            vid_id = item['id'].get('videoId', '')
            snippet = item.get('snippet', {})
            view_count = views_map.get(vid_id, 0)
            videos.append({
                "video_id": vid_id,
                "title": snippet.get('title', ''),
                "channel": snippet.get('channelTitle', ''),
                "published": snippet.get('publishedAt', '')[:10],
                "thumbnail": snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                "url": f"https://youtube.com/watch?v={vid_id}",
                "views": view_count,
                "views_display": format_views(view_count)
            })

        videos.sort(key=lambda x: x['views'], reverse=True)
        total_views = sum(v['views'] for v in videos)

        return {
            "video_count": len(videos),
            "videos": videos[:5],
            "total_views": format_views(total_views),
            "top_title": videos[0]['title'] if videos else ""
        }
    except Exception as e:
        print(f"    YouTube error: {e}")
        return {"video_count": 0, "videos": [], "total_views": "0", "top_title": ""}


def format_views(n):
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


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


def analyze_with_groq(all_data):
    print("Groq AI analysis ho rahi hai...")
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json"
        }
        prompt = f"""You are an AI content strategy assistant for Indian YouTube & Instagram creators.
Here is real trending data from India right now:
{json.dumps(all_data, ensure_ascii=False)}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "topics": [
    {{
      "title": "Short catchy Hinglish topic name",
      "category": "tech/finance/politics/incidents/business/startups",
      "trend_score": 85,
      "fact_status": "verified/partial/misleading",
      "youtube_videos": "45K",
      "youtube_views": "890M",
      "ig_hashtag": "#example",
      "ig_reels": "8K",
      "ig_views": "980K",
      "cross_platform": true,
      "since": "2 din se",
      "sources": "Times of India, NDTV",
      "yt_score": 85,
      "ig_score": 74
    }}
  ],
  "recommendations": [
    {{
      "title": "Catchy Hinglish video title",
      "score": 93,
      "reason": "Short reason in Hinglish",
      "platform": "both/youtube/instagram"
    }}
  ],
  "trending_audios": [
    {{
      "name": "Audio name",
      "usage": "500K reels",
      "match": "Kab use karo"
    }}
  ],
  "stats": {{
    "total_topics": 10,
    "verified_count": 7,
    "total_views": "8.2B",
    "top_category": "Finance"
  }}
}}"""

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.7
        }
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=30
        )
        text = r.json()['choices'][0]['message']['content'].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Groq error: {e}")
        return {}


def save_to_supabase(analysis, raw_videos):
    print("Supabase mein save ho raha hai...")
    record = {
        "fetched_at": datetime.utcnow().isoformat(),
        "topics": analysis.get('topics', []),
        "recommendations": analysis.get('recommendations', []),
        "trending_audios": analysis.get('trending_audios', []),
        "stats": analysis.get('stats', {}),
        "youtube_videos": raw_videos
    }
    supabase.table('trendiq_data').insert(record).execute()
    print("Save ho gaya!")


def main():
    print("=" * 50)
    print(f"TrendIQ Start: {datetime.utcnow()}")
    print("=" * 50)

    all_raw_data = []
    all_videos = {}

    for topic in TOPICS:
        print(f"\nTopic: {topic['query']}")
        yt_data   = fetch_youtube_videos(topic['query'])
        gt_score  = fetch_google_trends(topic['query'])
        news_data = fetch_news(topic['query'])

        all_videos[topic['query']] = yt_data.get('videos', [])

        all_raw_data.append({
            "topic":        topic['query'],
            "category":     topic['category'],
            "hashtag":      topic['hashtag'],
            "google_score": gt_score,
            "yt_videos":    yt_data['video_count'],
            "yt_top_title": yt_data['top_title'],
            "yt_views":     yt_data['total_views'],
            "news_count":   news_data['count'],
            "news_sources": news_data['sources'],
        })

    analysis = analyze_with_groq(all_raw_data)

    if not analysis.get('topics'):
        print("Groq fallback — raw data se topics bana raha hai")
        sorted_data = sorted(all_raw_data, key=lambda x: x['google_score'], reverse=True)
        analysis = {
            "topics": [
                {
                    "title": t["topic"].replace(" 2025", "").replace(" India", " — India"),
                    "category": t["category"],
                    "trend_score": t["google_score"],
                    "fact_status": "partial",
                    "youtube_videos": str(t["yt_videos"]) + " videos",
                    "youtube_views": t["yt_views"],
                    "ig_hashtag": "#" + t["hashtag"],
                    "ig_reels": "N/A",
                    "ig_views": "N/A",
                    "cross_platform": False,
                    "since": "aaj",
                    "sources": ", ".join(t["news_sources"]) if t["news_sources"] else "NewsAPI",
                    "yt_score": t["google_score"],
                    "ig_score": max(0, t["google_score"] - 15)
                }
                for t in sorted_data[:10]
            ],
            "recommendations": [
                {
                    "title": sorted_data[0]["topic"].replace(" 2025", "") + " pe video banao",
                    "score": sorted_data[0]["google_score"],
                    "reason": "Abhi India mein sabse zyada trending hai",
                    "platform": "youtube"
                },
                {
                    "title": sorted_data[1]["topic"].replace(" 2025", "") + " — Analysis",
                    "score": sorted_data[1]["google_score"],
                    "reason": "High news coverage + YouTube views",
                    "platform": "both"
                }
            ],
            "trending_audios": [],
            "stats": {
                "total_topics": len(all_raw_data),
                "verified_count": len([t for t in all_raw_data if t['news_count'] > 2]),
                "total_views": "Calculating...",
                "top_category": sorted_data[0]["category"]
            }
        }

    save_to_supabase(analysis, all_videos)

    print("\n" + "=" * 50)
    print("TrendIQ Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
