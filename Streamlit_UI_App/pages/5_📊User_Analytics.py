import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from utils import fetch_user_jobs

st.set_page_config(page_title="User Analytics", layout="wide")

# CSS for styling
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

body {
    background-color: #F9F9F9;
    font-family: "Helvetica Neue", Arial, sans-serif;
    margin: 0;
    padding: 0;
    color: #000000; /* Black text everywhere */
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Ensure user is logged in
if 'access_token' not in st.session_state or st.session_state['access_token'] is None:
    st.warning("You need to log in to view user analytics.")
    st.stop()

# Fetch user jobs
def fetch_user_jobs_data():
    try:
        return fetch_user_jobs(st.session_state['access_token'])
    except Exception as e:
        st.error(f"Error fetching user analytics data: {e}")
        return []

user_jobs = fetch_user_jobs_data()

st.title("📊 User Analytics")
st.markdown("---")

if user_jobs:
    st.write(f"Found {len(user_jobs)} saved job(s).")

    # Convert data into a Pandas DataFrame
    df = pd.DataFrame(user_jobs)

    # Add filters
    st.header("Filters")
    col1, col2, col3, col4, col5 = st.columns(5)

    # Filter by Location
    if "LOCATION" in df.columns:
        with col1:
            unique_locations = ["All"] + sorted(df["LOCATION"].dropna().unique())
            selected_locations = st.multiselect("Filter by Location", unique_locations, default=["All"])
            if "All" not in selected_locations:
                df = df[df["LOCATION"].isin(selected_locations)]

    # Filter by Company
    if "COMPANY" in df.columns:
        with col2:
            unique_companies = ["All"] + sorted(df["COMPANY"].dropna().unique())
            selected_companies = st.multiselect("Filter by Company", unique_companies, default=["All"])
            if "All" not in selected_companies:
                df = df[df["COMPANY"].isin(selected_companies)]

    # Filter by Status
    if "STATUS" in df.columns:
        with col3:
            unique_status = ["All"] + sorted(df["STATUS"].dropna().unique())
            selected_status = st.multiselect("Filter by Status", unique_status, default=["All"])
            if "All" not in selected_status:
                df = df[df["STATUS"].isin(selected_status)]

    # Filter by Posted Date
    if "POSTED_DATE" in df.columns:
        with col4:
            df["POSTED_DATE"] = pd.to_datetime(df["POSTED_DATE"], errors="coerce")
            unique_dates = ["All"] + sorted(df["POSTED_DATE"].dropna().astype(str).unique())
            selected_dates = st.multiselect("Filter by Posted Dates", unique_dates, default=["All"])
            if "All" not in selected_dates:
                selected_dates = pd.to_datetime(selected_dates)
                df = df[df["POSTED_DATE"].isin(selected_dates)]

    # Keyword Search
    with col5:
        search_query = st.text_input("Search by Keyword", "")
        if search_query:
            df = df[
                df["TITLE"].str.contains(search_query, case=False, na=False)
                | df["DESCRIPTION"].str.contains(search_query, case=False, na=False)
            ]

    # Display filtered DataFrame
    st.subheader("Filtered User Saved Jobs")
    st.dataframe(df)

    # ----- Analytics Section -----
    st.markdown("---")
    st.header("Analytics")

    # Total Jobs Saved
    st.subheader("📋 Total Jobs Saved")
    st.write(f"Total jobs saved after filtering: **{len(df)}**")

    # Jobs by Status
    if "STATUS" in df.columns:
        st.subheader("🟢 Jobs by Status")
        status_counts = df["STATUS"].value_counts()
        st.bar_chart(status_counts)
        st.write(status_counts)

    # Jobs by Location
    if "LOCATION" in df.columns:
        st.subheader("📍 Jobs by Location")
        location_counts = df["LOCATION"].value_counts().head(10)
        st.bar_chart(location_counts)
        st.write(location_counts)

    # Jobs Posted Over Time
    if "POSTED_DATE" in df.columns:
        st.subheader("🕒 Jobs Saved Over Time")
        jobs_over_time = df["POSTED_DATE"].value_counts().sort_index()
        st.line_chart(jobs_over_time)
        st.write(jobs_over_time)

    # Top Job Titles
    if "TITLE" in df.columns:
        st.subheader("💼 Top Job Titles")
        title_counts = df["TITLE"].value_counts().head(10)
        st.bar_chart(title_counts)
        st.write(title_counts)

    # Top Companies
    if "COMPANY" in df.columns:
        st.subheader("🏢 Top Companies")
        company_counts = df["COMPANY"].value_counts().head(10)
        st.bar_chart(company_counts)
        st.write(company_counts)

    # Word Cloud for Job Highlights
    if "JOB_HIGHLIGHTS" in df.columns:
        st.subheader("📖 Key Skills and Highlights (Word Cloud)")
        highlights_text = " ".join(df["JOB_HIGHLIGHTS"].dropna())
        wordcloud = WordCloud(width=800, height=400, background_color="white").generate(highlights_text)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        st.pyplot(plt)

    # Salary Range (if available)
    if "DESCRIPTION" in df.columns:
        st.subheader("💵 Salary Mentions")
        salary_keywords = df["DESCRIPTION"].str.extract(r"(\$[\d,]+)").dropna()
        if not salary_keywords.empty:
            st.write(f"Found {len(salary_keywords)} salary mentions in job descriptions.")
            st.write(salary_keywords[0].value_counts().head(10))
        else:
            st.write("No salary information found.")

    # Download Analytics Data
    st.subheader("📥 Download Filtered Data")
    st.download_button(
        label="Download Filtered User Data as CSV",
        data=df.to_csv(index=False),
        file_name="user_analytics.csv",
        mime="text/csv"
    )
else:
    st.info("No saved jobs found for the user.")
