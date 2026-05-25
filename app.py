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
TIKTOK_DAILY_LIMIT = 5
INSTAGRAM_DAILY_LIMIT = 5
TWITTER_DAILY_LIMIT = 5


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
        "Instagram": "Instagram_Daily",
        "Twitter": "Twitter_Daily",
    }

    sheet_name = sheet_map.get(platform)
    df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

    if "Keyword" not in df.columns:
        st.error(f"The sheet '{sheet_name}' must contain a column named 'Keyword'.")
        return pd.DataFrame(columns=["Project", "Keyword", "Platform"])

    all_data = []

    for keyword in df["Keyword"].dropna().tolist():
        keyword = str(keyword).strip()

        if keyword and keyword.upper() != "DO NOT USE":
            all_data.append({
                "Project": sheet_name,
                "Keyword": keyword,
                "Platform": platform
            })

    return pd.DataFrame(all_data)


def search_google_query(keyword, platform_name, query):
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
            "Platform": platform_name,
            "Keyword": keyword,
            "Title / Content": item.get("title", ""),
            "Snippet": item.get("snippet", ""),
            "URL": item.get("link", ""),
            "Alert Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        results.append(add_priority_fields(result))

    return results


def search_google_site(keyword, platform_name, site_domain):
    query = f'site:{site_domain} "{keyword}"'
    return search_google_query(keyword, platform_name, query)


def search_facebook(keyword):
    return search_google_site(keyword, "Facebook", "facebook.com")


def search_instagram(keyword):
    return search_google_site(keyword, "Instagram", "instagram.com")


def search_twitter(keyword):
    query = f'(site:x.com OR site:twitter.com) "{keyword}"'
    return search_google_query(keyword, "Twitter", query)


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

def deduplicate_results(df):
    if "URL" in df.columns:
        df = df.drop_duplicates(subset=["URL"], keep="first")

    if "Title / Content" in df.columns and "Keyword" in df.columns:
        df = df.drop_duplicates(subset=["Platform", "Keyword", "Title / Content"], keep="first")

    return df

def run_platform_tab(platform, limit, uploader_key, search_func, output_columns, download_name):
    st.header(f"{platform} Daily Rolling Search")
    st.info(f"Daily keyword limit: {limit}")

    uploaded_file = st.file_uploader(
        f"Upload Daily {platform} Keyword Excel",
        type=["xlsx"],
        key=uploader_key
    )

    if uploaded_file:
        df = parse_keyword_excel(uploaded_file, platform)
        st.info(f"Current keyword count: {len(df)}")

        if len(df) > limit:
            st.error(f"Quota exceeded! Daily limit is {limit}.")
            st.dataframe(df)
        else:
            st.success("Quota check passed")
            st.dataframe(df)

            if st.button(f"Run {platform} Search"):
                all_results = []

                with st.spinner(f"Searching {platform} public results..."):
                    for _, row in df.iterrows():
                        try:
                            results = search_func(row["Keyword"])

                            for r in results:
                                r["Project"] = row["Project"]
                                all_results.append(r)

                        except Exception as e:
                            st.error(f"Error searching {row['Keyword']}: {e}")

if all_results:
    final_df = deduplicate_results(pd.DataFrame(all_results))
    final_df = sort_by_priority(final_df)

    final_df = final_df[output_columns]

                    st.success(f"Found {len(final_df)} {platform} possible matches")
                    st.dataframe(final_df)

                    st.download_button(
                        label=f"Download {platform} Alert Excel",
                        data=convert_df_to_excel(final_df),
                        file_name=download_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning(f"No {platform} results found")


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Facebook Daily Rolling Search",
    "YouTube Daily Rolling Search",
    "TikTok Daily Rolling Search",
    "Instagram Daily Rolling Search",
    "Twitter Daily Rolling Search"
])


common_columns = [
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

youtube_columns = [
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

tiktok_columns = [
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


with tab1:
    run_platform_tab(
        platform="Facebook",
        limit=FACEBOOK_DAILY_LIMIT,
        uploader_key="facebook",
        search_func=search_facebook,
        output_columns=common_columns,
        download_name="facebook_alert_results.xlsx"
    )


with tab2:
    run_platform_tab(
        platform="YouTube",
        limit=YOUTUBE_DAILY_LIMIT,
        uploader_key="youtube",
        search_func=search_youtube,
        output_columns=youtube_columns,
        download_name="youtube_alert_results.xlsx"
    )


with tab3:
    run_platform_tab(
        platform="TikTok",
        limit=TIKTOK_DAILY_LIMIT,
        uploader_key="tiktok",
        search_func=search_tiktok,
        output_columns=tiktok_columns,
        download_name="tiktok_alert_results.xlsx"
    )


with tab4:
    run_platform_tab(
        platform="Instagram",
        limit=INSTAGRAM_DAILY_LIMIT,
        uploader_key="instagram",
        search_func=search_instagram,
        output_columns=common_columns,
        download_name="instagram_alert_results.xlsx"
    )


with tab5:
    run_platform_tab(
        platform="Twitter",
        limit=TWITTER_DAILY_LIMIT,
        uploader_key="twitter",
        search_func=search_twitter,
        output_columns=common_columns,
        download_name="twitter_alert_results.xlsx"
    )
