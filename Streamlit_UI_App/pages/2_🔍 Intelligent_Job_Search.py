import streamlit as st
from utils import search_jobs, save_job

st.set_page_config(page_title="Job Search", layout="centered")

# CSS for styling with all black text
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

/* Container styling */
section.main > div {
    background: #FFFFFF;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    border-radius: 10px;
    padding: 2rem;
    margin-top: 2rem;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
}

/* Titles and headings */
h1, h2, h3, h4 {
    font-weight: 600;
    text-align: center;
    margin-bottom: 1rem;
    color: 000000;
}

/* Job card styling */
.job-card {
    background: #FAFAFA;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    color: #000000;
    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    transition: box-shadow 0.3s ease;
}
.job-card:hover {
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
.job-card h3 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1.1rem;
}
.job-card p {
    margin: 0 0 0.3rem;
    font-size: 0.9rem;
}

/* Job details card */
.job-details-card {
    background: #FAFAFA;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    margin-bottom: 1.5rem;
    color: #000000;
}

.job-details-row {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
}

.job-details-col {
    flex: 1 1 calc(50% - 1rem);
    min-width: 200px;
}

.job-details-label {
    font-weight: 600;
    display: inline-block;
    margin-bottom: 0.2rem;
    color: 000000;
    font-size: 0.95rem;
}

.job-details-value {
    display: block;
    margin-bottom: 1rem;
    word-wrap: break-word;
    font-size: 0.95rem;
    color: 000000;
}

/* Buttons */
.stButton button {
    background: #2563EB;
    color: #FFFFFF !important;
}

.stButton button:hover {
    background: #1E40AF;
    cursor: pointer;
}

/* Inputs */
textarea, input {
    border: 1px solid #D1D5DB !important;
    border-radius: 10px !important;
}

/* Separator */
hr {
    border: none;
    border-top: 1px solid #E5E7EB;
    margin: 2rem 0;
}

/* Footer */
.footer {
    text-align: center;
    font-size: 0.9rem;
    margin-top: 2rem;
    color: #000000;
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
if 'search_performed' not in st.session_state:
    st.session_state['search_performed'] = False

# Ensure user is logged in
if st.session_state['access_token'] is None:
    st.warning("You need to log in to search for jobs.")
    st.stop()

st.title("Job Search")
st.markdown("---")
# Explanation for the Job Search page
st.write(
    """
    Use the search box below to find job listings that match your interests.  
    Once you see the search results, you can explore the details of any job by clicking the "View Details" button and in the details page use "Save Job" button to save the job details.
    """
)
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
    if 'selected_saved_job_index' in st.session_state:
        st.session_state['selected_saved_job_index'] = None
    st.session_state['search_performed'] = False

# Functions to display content
def show_job_list(jobs):
    st.markdown("---")
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
    st.markdown("---")
    st.markdown(f"<h2>{job.get('TITLE', 'No Title')}</h2>", unsafe_allow_html=True)

    # Job details
    st.markdown('<div class="job-details-row">', unsafe_allow_html=True)

    # Left Column
    st.markdown('<div class="job-details-col">', unsafe_allow_html=True)
    st.markdown(f'<span class="job-details-label">Job ID:</span><span class="job-details-value">{job.get("JOB_ID", "Unknown")}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="job-details-label">Company:</span><span class="job-details-value">{job.get("COMPANY", "Unknown")}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="job-details-label">Location:</span><span class="job-details-value">{job.get("LOCATION", "Unknown")}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="job-details-label">Posted Date:</span><span class="job-details-value">{job.get("POSTED_DATE", "Unknown")}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Right Column
    st.markdown('<div class="job-details-col">', unsafe_allow_html=True)
    description = job.get("DESCRIPTION", "No Description")
    highlights = job.get("JOB_HIGHLIGHTS", "Unknown")
    apply_links = job.get("APPLY_LINKS", "#")

    st.markdown(f'<span class="job-details-label">Description:</span><span class="job-details-value">{description}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="job-details-label">Highlights:</span><span class="job-details-value">{highlights}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="job-details-label">Application Link:</span><span class="job-details-value"><a href="{apply_links}" target="_blank">{apply_links}</a></span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # Close job-details-row
    st.markdown('</div>', unsafe_allow_html=True)  # Close job-details-card

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
            if 'selected_saved_job_index' in st.session_state:
                st.session_state['selected_saved_job_index'] = None
        else:
            st.error(f"Failed to save job: {response.json().get('detail', 'Unknown error')}")

    st.button("Back to Job List", key="back_to_job_list", on_click=go_back)

# Handle search input
search_query = st.text_input("Enter job search query")
search_button = st.button("Search", key="search_button")

if search_button and search_query:
    st.session_state['search_performed'] = True
    with st.spinner("Searching for jobs..."):
        response = search_jobs(search_query, st.session_state['access_token'])
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('data', [])
            st.session_state['search_results'] = jobs
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
        st.session_state['selected_search_job_index'] = None
        st.error("Selected job index is invalid. Please select a job again.")
        if st.session_state['search_results']:
            show_job_list(st.session_state['search_results'])
else:
    if st.session_state['search_results']:
        show_job_list(st.session_state['search_results'])
    elif st.session_state['search_performed']:  # Show only if search was performed
        st.markdown("---")
        st.warning("No jobs found for your search query. Please try a different query.")

st.markdown("---")
st.button("Logout", on_click=logout, key="logout_button")
