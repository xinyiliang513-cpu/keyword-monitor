import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Keyword Leakage Monitor", layout="wide")
st.title("🔍 Keyword Leakage Monitor")

SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
APIFY_TOKEN = st.secrets["APIFY_TOKEN"]

FACEBOOK_DAILY_LIMIT = 10
YOUTUBE_DAILY_LIMIT = 10
TIKTOK_DAILY_LIMIT = 10


def calculate_priority(keyword, title="", snippet="", url="", author=""):
    keyword = str(keyword).lower().strip()
    text = f"{title} {snippet} {url} {author}".lower()

    score = 0
    reasons = []

    if keyword and keyword in text:
        score += 50
        reasons.append("Exact keyword matched")

    if keyword and keyword in str(title).lower():
        score += 30
        reasons.append("Keyword matched in title/content")

    if keyword and keyword in str(snippet).lower():
        score += 20
        reasons.append("Keyword matched in description/snippet")

    if keyword and keyword in str(url).lower():
        score += 20
        reasons.append("Keyword matched in URL")

    if keyword and keyword in str(author).lower():
        score += 20
        reasons.append("Keyword matched in author/account")

    if score >= 70:
        priority = "High"
    elif score >= 40:
        priority = "Medium"
    else:
        priority = "Low"

    return score, priority, "; ".join(reasons) if reasons else "Weak relevance only"


def add_priority_fields(result):
    score, priority, reason = calculate_priority(
        keyword=result.get("Keyword", ""),
        title=result.get("Title / Content", ""),
        snippet=result.get("Snippet", ""),
        url=result.get("URL", ""),
        author=result.get("Author", "") or result.get("Channel", "")
    )

    result["Match Score"] = score
    result["Priority"] = priority
    result["Match Reason"] = reason
    result["Review Result"] = ""
    result["Reviewer Notes"] = ""

    return result


def parse_keyword_excel(uploaded_file, platform):
    sheet_map = {
        "Facebook": "Facebook_Daily",
        "YouTube": "YouTube_Daily",
        "TikTok": "TikTok_Daily",
    }

    sheet_name = sheet_map.get(platform)
    df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

    if "Keyword" not in df.columns:
        st.error(f"The sheet '{sheet_name}' must contain a column named 'Keyword'.")
        return pd.DataFrame(columns=["Project", "Keyword", "Platform"])

    all_data = []

    for keyword in df["Keyword"].dropna().tolist():
        keyword = str(keyword).strip()
        if keyword:
            all_data.append({
                "Project": sheet_name,
                "Keyword": keyword,
                "Platform": platform
            })

    return pd.DataFrame(all_data)


def search_facebook(keyword):
    query = f'site:facebook.com "{keyword}"'
    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 5
    }

    response = requests.get(url, params=params, timeout=20)
    data = response.json()

    results = []

    for item in data.get("organic_results", [])[:5]:
        result = {
            "Platform": "Facebook",
            "Keyword": keyword,
            "Title / Content": item.get("title", ""),
            "Snippet": item.get("snippet", ""),
            "URL": item.get("link", ""),
            "Alert Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        results.append(add_priority_fields(result))

    return results


def search_youtube(keyword):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": keyword,
        "key": YOUTUBE_API_KEY,
        "maxResults": 5,
        "type": "video"
    }

    response = requests.get(url, params=params, timeout=20)
    data = response.json()

    results = []

    for item in data.get("items", []):
        video_id = item["id"].get("videoId", "")
        snippet = item.get("snippet", {})

        result = {
            "Platform": "YouTube",
            "Keyword": keyword,
            "Title / Content": snippet.get("title", ""),
            "Channel": snippet.get("channelTitle", ""),
            "Published Time": snippet.get("publishedAt", ""),
            "Snippet": snippet.get("description", ""),
            "URL": f"https://www.youtube.com/watch?v={video_id}",
            "Alert Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        results.append(add_priority_fields(result))

    return results


def search_tiktok(keyword):
    url = "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items"

    params = {"token": APIFY_TOKEN}

    payload = {
        "searchQueries": [keyword],
        "resultsPerPage": 10,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
        "shouldDownloadSlideshowImages": False
    }

    response = requests.post(url, params=params, json=payload, timeout=180)

    if response.status_code not in [200, 201]:
        raise Exception(f"Apify API error: {response.status_code} - {response.text}")

    data = response.json()
    results = []

    for item in data:
        author_meta = item.get("authorMeta", {}) or {}
        video_meta = item.get("videoMeta", {}) or {}
        music_meta = item.get("musicMeta", {}) or {}

        video_url = (
            item.get("webVideoUrl")
            or item.get("url")
            or item.get("videoUrl")
            or ""
        )

        result = {
            "Platform": "TikTok",
            "Keyword": keyword,
            "Title / Content": item.get("text", ""),
            "Author": author_meta.get("name", ""),
            "Author Nickname": author_meta.get("nickName", ""),
            "Published Time": item.get("createTimeISO", ""),
            "Play Count": item.get("playCount", ""),
            "Like Count": item.get("diggCount", ""),
            "Comment Count": item.get("commentCount", ""),
            "Share Count": item.get("shareCount", ""),
            "Bookmark Count": item.get("collectCount", ""),
            "Duration": video_meta.get("duration", ""),
            "Music": music_meta.get("musicName", ""),
            "Snippet": item.get("text", ""),
            "URL": video_url,
            "Alert Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        results.append(add_priority_fields(result))

    return results


def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Alert Results")
    return output.getvalue()


def sort_by_priority(df):
    priority_order = {"High": 1, "Medium": 2, "Low": 3}
    df["Priority Order"] = df["Priority"].map(priority_order)
    df = df.sort_values(by=["Priority Order", "Match Score"], ascending=[True, False])
    df = df.drop(columns=["Priority Order"])
    return df


tab1, tab2, tab3 = st.tabs([
    "Facebook Daily Rolling Search",
    "YouTube Daily Rolling Search",
    "TikTok Daily Rolling Search"
])


with tab1:
    st.header("Facebook Daily Rolling Search")
    st.info(f"Daily keyword limit: {FACEBOOK_DAILY_LIMIT}")

    fb_file = st.file_uploader("Upload Daily Facebook Keyword Excel", type=["xlsx"], key="facebook")

    if fb_file:
        fb_df = parse_keyword_excel(fb_file, "Facebook")
        st.info(f"Current keyword count: {len(fb_df)}")

        if len(fb_df) > FACEBOOK_DAILY_LIMIT:
            st.error(f"Quota exceeded! Daily limit is {FACEBOOK_DAILY_LIMIT}.")
            st.dataframe(fb_df)
        else:
            st.success("Quota check passed")
            st.dataframe(fb_df)

            if st.button("Run Facebook Search"):
                search_results = []

                with st.spinner("Searching Facebook public results..."):
                    for _, row in fb_df.iterrows():
                        try:
                            results = search_facebook(row["Keyword"])
                            for r in results:
                                r["Project"] = row["Project"]
                                search_results.append(r)
                        except Exception as e:
                            st.error(f"Error searching {row['Keyword']}: {e}")

                if search_results:
                    final_df = sort_by_priority(pd.DataFrame(search_results))

                    final_df = final_df[
                        [
                            "Priority",
                            "Match Score",
                            "Match Reason",
                            "Platform",
                            "Project",
                            "Keyword",
                            "Title / Content",
                            "Snippet",
                            "URL",
                            "Alert Time",
                            "Review Result",
                            "Reviewer Notes"
                        ]
                    ]

                    st.success(f"Found {len(final_df)} possible matches")
                    st.dataframe(final_df)

                    st.download_button(
                        label="Download Facebook Alert Excel",
                        data=convert_df_to_excel(final_df),
                        file_name="facebook_alert_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No results found")


with tab2:
    st.header("YouTube Daily Rolling Search")
    st.info(f"Daily keyword limit: {YOUTUBE_DAILY_LIMIT}")

    yt_file = st.file_uploader("Upload Daily YouTube Keyword Excel", type=["xlsx"], key="youtube")

    if yt_file:
        yt_df = parse_keyword_excel(yt_file, "YouTube")
        st.info(f"Current keyword count: {len(yt_df)}")

        if len(yt_df) > YOUTUBE_DAILY_LIMIT:
            st.error(f"Quota exceeded! Daily limit is {YOUTUBE_DAILY_LIMIT}.")
            st.dataframe(yt_df)
        else:
            st.success("Quota check passed")
            st.dataframe(yt_df)

            if st.button("Run YouTube Search"):
                yt_results = []

                with st.spinner("Searching YouTube public videos..."):
                    for _, row in yt_df.iterrows():
                        try:
                            results = search_youtube(row["Keyword"])
                            for r in results:
                                r["Project"] = row["Project"]
                                yt_results.append(r)
                        except Exception as e:
                            st.error(f"Error searching {row['Keyword']}: {e}")

                if yt_results:
                    yt_final_df = sort_by_priority(pd.DataFrame(yt_results))

                    yt_final_df = yt_final_df[
                        [
                            "Priority",
                            "Match Score",
                            "Match Reason",
                            "Platform",
                            "Project",
                            "Keyword",
                            "Title / Content",
                            "Channel",
                            "Published Time",
                            "Snippet",
                            "URL",
                            "Alert Time",
                            "Review Result",
                            "Reviewer Notes"
                        ]
                    ]

                    st.success(f"Found {len(yt_final_df)} YouTube results")
                    st.dataframe(yt_final_df)

                    st.download_button(
                        label="Download YouTube Alert Excel",
                        data=convert_df_to_excel(yt_final_df),
                        file_name="youtube_alert_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No YouTube results found")


with tab3:
    st.header("TikTok Daily Rolling Search")
    st.info(f"Daily keyword limit: {TIKTOK_DAILY_LIMIT}")

    tk_file = st.file_uploader("Upload Daily TikTok Keyword Excel", type=["xlsx"], key="tiktok")

    if tk_file:
        tk_df = parse_keyword_excel(tk_file, "TikTok")
        st.info(f"Current keyword count: {len(tk_df)}")

        if len(tk_df) > TIKTOK_DAILY_LIMIT:
            st.error(f"Quota exceeded! Daily limit is {TIKTOK_DAILY_LIMIT}.")
            st.dataframe(tk_df)
        else:
            st.success("Quota check passed")
            st.dataframe(tk_df)

            if st.button("Run TikTok Search"):
                tk_results = []

                with st.spinner("Searching TikTok public videos..."):
                    for _, row in tk_df.iterrows():
                        try:
                            results = search_tiktok(row["Keyword"])
                            for r in results:
                                r["Project"] = row["Project"]
                                tk_results.append(r)
                        except Exception as e:
                            st.error(f"Error searching {row['Keyword']}: {e}")

                if tk_results:
                    tk_final_df = sort_by_priority(pd.DataFrame(tk_results))

                    tk_final_df = tk_final_df[
                        [
                            "Priority",
                            "Match Score",
                            "Match Reason",
                            "Platform",
                            "Project",
                            "Keyword",
                            "Title / Content",
                            "Author",
                            "Author Nickname",
                            "Published Time",
                            "Play Count",
                            "Like Count",
                            "Comment Count",
                            "Share Count",
                            "Bookmark Count",
                            "Duration",
                            "Music",
                            "URL",
                            "Alert Time",
                            "Review Result",
                            "Reviewer Notes"
                        ]
                    ]

                    st.success(f"Found {len(tk_final_df)} TikTok results")
                    st.dataframe(tk_final_df)

                    st.download_button(
                        label="Download TikTok Alert Excel",
                        data=convert_df_to_excel(tk_final_df),
                        file_name="tiktok_alert_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No TikTok results found")
