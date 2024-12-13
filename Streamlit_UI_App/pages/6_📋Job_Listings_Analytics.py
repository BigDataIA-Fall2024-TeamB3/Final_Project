import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from utils import get_job_listings

st.set_page_config(page_title="Job Listings Analytics", layout="wide")

# CSS for styling (optional)
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
    st.warning("You need to log in to view job listings.")
    st.stop()

# Fetch job listings
def fetch_job_listings():
    try:
        response = get_job_listings(st.session_state['access_token'])
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch job listings: {response.json().get('detail', 'Unknown error')}")
            return []
    except Exception as e:
        st.error(f"Error fetching job listings: {str(e)}")
        return []

# Fetch the job listings
job_listings = fetch_job_listings()

st.title("📋 Job Listings Analytics")
st.markdown("---")

if job_listings:
    st.write(f"Found {len(job_listings)} job listing(s).")

    # Convert data into a Pandas DataFrame
    df = pd.DataFrame(job_listings)

    # Add filters
    st.header("Filters")
    col1, col2, col3, col4, col5 = st.columns(5)

    # Filter by Location (Multi-select with "All" option)
    if "LOCATION" in df.columns:
        with col1:
            unique_locations = ["All"] + sorted(df["LOCATION"].dropna().unique())
            selected_locations = st.multiselect("Filter by Location", unique_locations, default=["All"])
            if "All" not in selected_locations:
                df = df[df["LOCATION"].isin(selected_locations)]

    # Filter by Company (Multi-select with "All" option)
    if "COMPANY" in df.columns:
        with col2:
            unique_companies = ["All"] + sorted(df["COMPANY"].dropna().unique())
            selected_companies = st.multiselect("Filter by Company", unique_companies, default=["All"])
            if "All" not in selected_companies:
                df = df[df["COMPANY"].isin(selected_companies)]

    # Filter by Search Query (Multi-select with "All" option)
    if "SEARCH_QUERY" in df.columns:
        with col3:
            unique_queries = ["All"] + sorted(df["SEARCH_QUERY"].dropna().unique())
            selected_queries = st.multiselect("Filter by Search Query", unique_queries, default=["All"])
            if "All" not in selected_queries:
                df = df[df["SEARCH_QUERY"].isin(selected_queries)]

    # Filter by Date Range (Multi-select for individual dates with "All" option)
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
    st.subheader("Filtered Job Listings Data")
    st.dataframe(df)

    # ----- Analytics Section -----
    st.markdown("---")
    st.header("Analytics")

    # Total Job Listings
    st.subheader("📊 Total Job Listings")
    st.write(f"Total job listings after filtering: **{len(df)}**")

    # Jobs by Location
    if "LOCATION" in df.columns:
        st.subheader("📍 Jobs by Location")
        location_counts = df["LOCATION"].value_counts().head(10)
        st.bar_chart(location_counts)
        st.write(location_counts)

    # Jobs by Company
    if "COMPANY" in df.columns:
        st.subheader("🏢 Jobs by Company")
        company_counts = df["COMPANY"].value_counts().head(10)
        st.bar_chart(company_counts)
        st.write(company_counts)

    # Posted Date Analysis
    if "POSTED_DATE" in df.columns:
        st.subheader("🕒 Jobs Posted Over Time")
        posted_date_counts = df["POSTED_DATE"].value_counts().sort_index()
        st.line_chart(posted_date_counts)
        st.write(posted_date_counts)

    # Top Job Titles
    if "TITLE" in df.columns:
        st.subheader("💼 Most Common Job Titles")
        title_counts = df["TITLE"].value_counts().head(10)
        st.bar_chart(title_counts)
        st.write(title_counts)

    # Skills and Highlights Analysis
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
        st.subheader("💵 Salary Insights")
        salary_keywords = df["DESCRIPTION"].str.extract(r"(\$[\d,]+)").dropna()
        if not salary_keywords.empty:
            st.write(f"Found {len(salary_keywords)} salary mentions in job descriptions.")
            salary_table = pd.DataFrame({
                "Job Title": df.loc[salary_keywords.index, "TITLE"],
                "Company": df.loc[salary_keywords.index, "COMPANY"],
                "Location": df.loc[salary_keywords.index, "LOCATION"],
                "Salary": salary_keywords[0]
            })
            st.write(salary_table)
        else:
            st.write("No salary information found.")

    # Download Analytics Data
    st.subheader("📥 Download Filtered Data")
    st.download_button(
        label="Download Filtered Job Listings as CSV",
        data=df.to_csv(index=False),
        file_name="filtered_job_listings.csv",
        mime="text/csv"
    )
else:
    st.info("No job listings found.")
