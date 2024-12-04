import streamlit as st
from utils import search_jobs

st.set_page_config(page_title="Job Search", layout="centered")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.job-card {
    border: 1px solid #ccc;
    padding: 10px;
    min-height: 150px; /* Adjust as desired */
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    border-radius: 5px;
    background: #f9f9f9;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    margin-bottom: 10px;
    color: #000;
}

.job-card h3 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1.1rem;
    color: #000;
}

.job-card p {
    margin: 0;
    font-size: 0.9rem;
    margin-bottom: 0.3rem;
    color: #000;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Initialize session state variables
if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None
if 'selected_job_index' not in st.session_state:
    st.session_state['selected_job_index'] = None
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []

if st.session_state['access_token'] is None:
    st.warning("You need to log in to search for jobs.")
    st.stop()

st.title("Job Search")

# Callback functions to update state
def select_job(index):
    st.session_state['selected_job_index'] = index

def go_back():
    st.session_state['selected_job_index'] = None

def logout():
    st.session_state['access_token'] = None
    st.session_state['search_results'] = []
    st.session_state['selected_job_index'] = None

# Functions to display content
def show_job_list(jobs):
    st.write(f"Found {len(jobs)} job(s).")
    for i, job in enumerate(jobs):
        title = job.get('TITLE', 'No Title')
        company = job.get('COMPANY', 'Unknown')
        location = job.get('LOCATION', 'Unknown')
        posted_date = job.get('POSTED_DATE', 'Unknown')

        job_card_html = f"""
        <div class="job-card">
            <h3>{title}</h3>
            <p><strong>Company:</strong> {company}</p>
            <p><strong>Location:</strong> {location}</p>
            <p><strong>Posted:</strong> {posted_date}</p>
        </div>
        """
        st.markdown(job_card_html, unsafe_allow_html=True)
        
        # Use on_click to set the job index in session state
        st.button("View Details", key=f"view_details_{i}", on_click=select_job, args=(i,))

def show_job_details(job):
    st.subheader(job.get('TITLE', 'No Title'))
    st.write(f"**Company:** {job.get('COMPANY', 'Unknown')}")
    st.write(f"**Location:** {job.get('LOCATION', 'Unknown')}")
    st.write(f"**Description:** {job.get('DESCRIPTION', 'No Description')}")
    st.write(f"**Job Highlights:** {job.get('JOB_HIGHLIGHTS', 'Unknown')}")
    st.write(f"**Posted Date:** {job.get('POSTED_DATE', 'Unknown')}")
    st.write(f"**Apply Here:** {job.get('APPLY_LINKS', 'Unknown')}")

    # Use on_click to reset selected_job_index
    st.button("Back", on_click=go_back)

# Handle search input
search_query = st.text_input("Enter job search query")
search_button = st.button("Search")

if search_button and search_query:
    with st.spinner("Searching for jobs..."):
        response = search_jobs(search_query, st.session_state['access_token'])
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('data', [])
            st.session_state['search_results'] = jobs
            st.session_state['selected_job_index'] = None
        else:
            st.error("Failed to fetch jobs. Please try again.")

# Decide what to display based on the updated state
if st.session_state['selected_job_index'] is not None:
    selected_job = st.session_state['search_results'][st.session_state['selected_job_index']]
    show_job_details(selected_job)
else:
    if st.session_state['search_results']:
        show_job_list(st.session_state['search_results'])

# Logout button at the bottom
st.button("Logout", on_click=logout)
