import streamlit as st
from utils import search_jobs, save_job

st.set_page_config(page_title="Job Search", layout="centered")

# CSS for styling with theme-aware design
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

body {
    font-family: "Helvetica Neue", Arial, sans-serif;
    margin: 0;
    padding: 0;
}

/* Light mode styles */
@media (prefers-color-scheme: light) {
    body {
        background-color: #F9F9F9;
        color: #000000;
    }
    section.main > div {
        background: #FFFFFF;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .job-card {
        background: #FAFAFA;
        border: 1px solid #D1D5DB;
        color: #000000;
    }
    .job-card h3 {
        color: #000000;
    }
    .job-details-card {
        background: #FAFAFA;
    }
    .job-details-label {
        color: #000000;
    }
    .job-details-value {
        color: #333333;
    }
    .stButton button {
        background: #2563EB;
        color: #FFFFFF !important;
    }
    .stButton button:hover {
        background: #1E40AF;
    }
    # input, textarea {
    #     color: #000000 !important;
    # }
}

/* Dark mode styles */
@media (prefers-color-scheme: dark) {
    body {
        background-color: #000000;
        color: #FFFFFF;
    }
    section.main > div {
        background: #1E1E1E;
        box-shadow: 0 2px 10px rgba(255,255,255,0.1);
    }
    .job-card {
        background: #2A2A2A;
        border: 1px solid #555555;
        color: #FFFFFF;
    }
    .job-card h3 {
        color: #FFFFFF;
    }
    .job-details-card {
        background: #2A2A2A;
    }
    .job-details-label {
        color: #FFFFFF;
    }
    .job-details-value {
        color: #DDDDDD;
    }
    .stButton button {
        background: #2563EB;
        color: #FFFFFF !important;
        border: none;
    }
    .stButton button:hover {
        background: #1E40AF;
    }
    # input, textarea {
    #     color: #FFFFFF !important;
    #     background: #333333 !important;
    #     border: 1px solid #555555 !important;
    # }
}

/* Common Styles (applied in both modes) */
section.main > div {
    padding: 2rem;
    border-radius: 10px;
    margin-top: 2rem;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
}

h1, h2, h3, h4 {
    font-weight: 600;
    margin-bottom: 1rem;
    text-align: center;
}

.job-card {
    padding: 1rem;
    min-height: 150px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    border-radius: 8px;
    margin-bottom: 1rem;
    transition: box-shadow 0.3s ease;
}

.job-card:hover {
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.job-card p {
    margin: 0 0 0.3rem;
    font-size: 0.9rem;
}

.job-details-card {
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    margin-bottom: 1.5rem;
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
    margin-right: 0.5rem;
    display: inline-block;
    margin-bottom: 0.2rem;
}

.job-details-value {
    margin-bottom: 1rem;
    display: block;
    word-wrap: break-word;
    font-size: 0.95rem;
}

.stButton button {
    border-radius: 6px;
    padding: 0.75rem 1.25rem;
    font-size: 0.95rem;
    margin-top: 0.5rem;
    transition: background 0.3s;
}

hr {
    border: none;
    border-top: 1px solid #E5E7EB;
    margin: 2rem 0;
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

st.markdown("---")
st.button("Logout", on_click=logout, key="logout_button")
