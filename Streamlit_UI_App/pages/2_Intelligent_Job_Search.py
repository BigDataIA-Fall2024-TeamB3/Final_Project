import streamlit as st
from utils import search_jobs, save_job

st.set_page_config(page_title="Job Search", layout="centered")

# CSS for styling
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.job-card {
    border: 1px solid #ccc;
    padding: 10px;
    min-height: 150px;
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
if 'selected_search_job_index' not in st.session_state:
    st.session_state['selected_search_job_index'] = None
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []

# Ensure user is logged in
if st.session_state['access_token'] is None:
    st.warning("You need to log in to search for jobs.")
    st.stop()

st.title("Job Search")

# Callback functions
def select_job(index):
    """Select a job by index."""
    st.session_state['selected_search_job_index'] = index

def go_back():
    """Clear selected job and go back to job list."""
    st.session_state['selected_search_job_index'] = None

def logout():
    """Clear session state and log out."""
    st.session_state['access_token'] = None
    st.session_state['search_results'] = []
    st.session_state['selected_search_job_index'] = None
    # Also reset saved jobs index if used
    if 'selected_saved_job_index' in st.session_state:
        st.session_state['selected_saved_job_index'] = None

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
        st.button("View Details", key=f"view_details_{i}", on_click=select_job, args=(i,))

def show_job_details(job):
    st.subheader(job.get('TITLE', 'No Title'))
    st.write(f"**Job ID:** {job.get('JOB_ID', 'Unknown')}")
    st.write(f"**Company:** {job.get('COMPANY', 'Unknown')}")
    st.write(f"**Location:** {job.get('LOCATION', 'Unknown')}")
    st.write(f"**Description:** {job.get('DESCRIPTION', 'No Description')}")
    st.write(f"**Highlights:** {job.get('JOB_HIGHLIGHTS', 'Unknown')}")
    st.write(f"**Posted Date:** {job.get('POSTED_DATE', 'Unknown')}")
    st.write(f"**Application Link:** {job.get('APPLY_LINKS', '#')}")

    # Save Job Button
    if st.button("Save Job"):
        job_details = {
            "job_id": job.get('JOB_ID', 'Unknown'),
            "title": job.get('TITLE', 'No Title'),
            "company": job.get('COMPANY', 'Unknown'),
            "location": job.get('LOCATION', 'Unknown'),
            "description": job.get('DESCRIPTION', 'No Description'),
            "job_highlights": job.get('JOB_HIGHLIGHTS', 'Unknown'),
            "apply_links": job.get('APPLY_LINKS', 'Unknown'),
            "posted_date": job.get('POSTED_DATE', 'Unknown'),
            "status": "Not Applied"
        }
        response = save_job(job_details, st.session_state['access_token'])
        if response.status_code == 200:
            st.success("Job saved successfully!")
            # After saving a job, reset selected indexes for saved jobs page if used
            if 'selected_saved_job_index' in st.session_state:
                st.session_state['selected_saved_job_index'] = None
        else:
            st.error(f"Failed to save job: {response.json().get('detail', 'Unknown error')}")

    st.button("Back to Job List", key="back_to_job_list", on_click=go_back)

# Handle search input
search_query = st.text_input("Enter job search query")
search_button = st.button("Search", key="search_button")

if search_button and search_query:
    with st.spinner("Searching for jobs..."):
        response = search_jobs(search_query, st.session_state['access_token'])
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('data', [])
            st.session_state['search_results'] = jobs
            # Reset selection whenever new search is done
            st.session_state['selected_search_job_index'] = None
        else:
            st.error("Failed to fetch jobs. Please try again.")

# Display job list or details based on the state
if st.session_state['selected_search_job_index'] is not None:
    idx = st.session_state['selected_search_job_index']
    if idx < len(st.session_state['search_results']):
        selected_job = st.session_state['search_results'][idx]
        show_job_details(selected_job)
    else:
        # Invalid index, reset and show list
        st.session_state['selected_search_job_index'] = None
        st.error("Selected job index is invalid. Please select a job again.")
        if st.session_state['search_results']:
            show_job_list(st.session_state['search_results'])
else:
    if st.session_state['search_results']:
        show_job_list(st.session_state['search_results'])

st.button("Logout", on_click=logout, key="logout_button")
