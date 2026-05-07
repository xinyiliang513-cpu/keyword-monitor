import streamlit as st
import pandas as pd

st.set_page_config(page_title="Keyword Leakage Monitor", layout="wide")

st.title("🔍 Keyword Leakage Monitor")

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

        st.dataframe(result_df)
