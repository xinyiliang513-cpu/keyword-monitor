import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Keyword Leakage Monitor", layout="wide")

st.title("🔍 Keyword Leakage Monitor")

SERPAPI_KEY = st.secrets["SERPAPI_KEY"]

FACEBOOK_DAILY_LIMIT = 10
YOUTUBE_DAILY_LIMIT = 10


def parse_keyword_excel(uploaded_file, platform):
    sheets = pd.read_excel(uploaded_file, sheet_name=None)

    all_data = []

    for project_name, df in sheets.items():
        for column in df.columns:
            keywords = df[column].dropna().tolist()

            for keyword in keywords:
                keyword = str(keyword).strip()

                if keyword:
                    all_data.append({
                        "Project": project_name,
                        "Language": column,
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

    if "organic_results" in data:
        for item in data["organic_results"][:5]:
            results.append({
                "Platform": "Facebook",
                "Keyword": keyword,
                "Title / Content": item.get("title", ""),
                "URL": item.get("link", ""),
                "Snippet": item.get("snippet", ""),
                "Alert Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return results


def convert_df_to_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Alert Results")

    return output.getvalue()


tab1, tab2 = st.tabs(["Facebook Daily Rolling Search", "YouTube Daily Rolling Search"])


# Facebook
with tab1:
    st.header("Facebook Daily Rolling Search")

    st.info(f"Daily keyword limit: {FACEBOOK_DAILY_LIMIT}")

    fb_file = st.file_uploader(
        "Upload Daily Facebook Keyword Excel",
        type=["xlsx"],
        key="facebook"
    )

    if fb_file:
        fb_df = parse_keyword_excel(fb_file, "Facebook")

        keyword_count = len(fb_df)

        st.info(f"Current keyword count: {keyword_count}")

        if keyword_count > FACEBOOK_DAILY_LIMIT:
            st.error(f"Quota exceeded! Daily limit is {FACEBOOK_DAILY_LIMIT}. Please upload no more than {FACEBOOK_DAILY_LIMIT} keywords.")
            st.dataframe(fb_df)
        else:
            st.success("Quota check passed")
            st.dataframe(fb_df)

            if st.button("Run Facebook Search"):
                search_results = []

                with st.spinner("Searching Facebook public results..."):
                    for _, row in fb_df.iterrows():
                        keyword = row["Keyword"]

                        try:
                            results = search_facebook(keyword)

                            for r in results:
                                r["Project"] = row["Project"]
                                r["Language"] = row["Language"]
                                search_results.append(r)

                        except Exception as e:
                            st.error(f"Error searching {keyword}: {e}")

                if search_results:
                    final_df = pd.DataFrame(search_results)

                    final_df = final_df[
                        [
                            "Platform",
                            "Project",
                            "Language",
                            "Keyword",
                            "Title / Content",
                            "Snippet",
                            "URL",
                            "Alert Time"
                        ]
                    ]

                    st.success(f"Found {len(final_df)} possible matches")
                    st.dataframe(final_df)

                    excel_data = convert_df_to_excel(final_df)

                    st.download_button(
                        label="Download Facebook Alert Excel",
                        data=excel_data,
                        file_name="facebook_alert_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No results found")


# YouTube
with tab2:
    st.header("YouTube Daily Rolling Search")

    st.info(f"Daily keyword limit: {YOUTUBE_DAILY_LIMIT}")

    yt_file = st.file_uploader(
        "Upload Daily YouTube Keyword Excel",
        type=["xlsx"],
        key="youtube"
    )

    if yt_file:
        yt_df = parse_keyword_excel(yt_file, "YouTube")

        keyword_count = len(yt_df)

        st.info(f"Current keyword count: {keyword_count}")

        if keyword_count > YOUTUBE_DAILY_LIMIT:
            st.error(f"Quota exceeded! Daily limit is {YOUTUBE_DAILY_LIMIT}. Please upload no more than {YOUTUBE_DAILY_LIMIT} keywords.")
            st.dataframe(yt_df)
        else:
            st.success("Quota check passed")
            st.dataframe(yt_df)

            st.warning("YouTube search API has not been connected yet. This tab currently only checks the daily keyword quota.")
