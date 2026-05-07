import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Keyword Leakage Monitor", layout="wide")

st.title("🔍 Keyword Leakage Monitor")
SERPAPI_KEY = st.secrets["SERPAPI_KEY"]

def search_facebook(keyword):

    query = f'site:facebook.com "{keyword}"'

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY
    }

    response = requests.get(url, params=params)

    data = response.json()

    results = []

    if "organic_results" in data:

        for item in data["organic_results"][:5]:

            results.append({
                "Keyword": keyword,
                "Title": item.get("title", ""),
                "Link": item.get("link", ""),
                "Snippet": item.get("snippet", "")
            })

    return results

tab1, tab2 = st.tabs(["Facebook Full Search", "YouTube Daily Search"])

# Facebook
with tab1:
    st.header("Facebook Full Keyword Search")

    fb_file = st.file_uploader(
        "Upload Full Facebook Keyword Excel",
        type=["xlsx"],
        key="facebook"
    )

    if fb_file:
        sheets = pd.read_excel(fb_file, sheet_name=None)

        all_data = []

        for project_name, df in sheets.items():
            for column in df.columns:
                keywords = df[column].dropna().tolist()

                for keyword in keywords:
                    all_data.append({
                        "Project": project_name,
                        "Language": column,
                        "Keyword": keyword,
                        "Platform": "Facebook"
                    })

        result_df = pd.DataFrame(all_data)

        st.success(f"Loaded {len(result_df)} keywords")

        st.dataframe(result_df)


# YouTube
with tab2:
    st.header("YouTube Daily Quota Search")

    yt_file = st.file_uploader(
        "Upload Daily YouTube Keyword Excel",
        type=["xlsx"],
        key="youtube"
    )

    DAILY_LIMIT = 60

    if yt_file:
        sheets = pd.read_excel(yt_file, sheet_name=None)

        all_data = []

        for project_name, df in sheets.items():
            for column in df.columns:
                keywords = df[column].dropna().tolist()

                for keyword in keywords:
                    all_data.append({
                        "Project": project_name,
                        "Language": column,
                        "Keyword": keyword,
                        "Platform": "YouTube"
                    })

        result_df = pd.DataFrame(all_data)

        keyword_count = len(result_df)

        st.info(f"Current keyword count: {keyword_count}")

        if keyword_count > DAILY_LIMIT:
            st.error(f"Quota exceeded! Daily limit is {DAILY_LIMIT}")
        else:
            st.success("Quota check passed")

if st.button("Run Facebook Search"):

    search_results = []

    for keyword in result_df["Keyword"]:

        try:
            results = search_facebook(keyword)

            for r in results:
                search_results.append(r)

        except Exception as e:
            st.error(f"Error searching {keyword}: {e}")

    if search_results:

        final_df = pd.DataFrame(search_results)

        st.success(f"Found {len(final_df)} possible matches")

        st.dataframe(final_df)

    else:
        st.warning("No results found")
