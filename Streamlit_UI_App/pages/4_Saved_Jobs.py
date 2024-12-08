import streamlit as st
from utils import get_saved_jobs, update_job_status, delete_saved_job

st.set_page_config(page_title="Saved Jobs", layout="centered")

# CSS for styling
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

# Ensure user is logged in
if 'access_token' not in st.session_state or st.session_state['access_token'] is None:
    st.warning("You need to log in to view saved jobs.")
    st.stop()

# Initialize session state variables
if 'selected_saved_job_index' not in st.session_state:
    st.session_state['selected_saved_job_index'] = None

def logout():
    """
    Clear session state and log out the user.
    """
    st.session_state['access_token'] = None
    st.session_state['selected_saved_job_index'] = None
    st.success("Logged out successfully!")

def fetch_saved_jobs():
    """
    Fetch saved jobs from the backend using the access token.
    """
    try:
        response = get_saved_jobs(st.session_state['access_token'])
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch saved jobs: {response.json().get('detail', 'Unknown error')}")
            return []
    except Exception as e:
        st.error(f"Error fetching saved jobs: {str(e)}")
        return []

# Callback to select a job
def select_job(index):
    st.session_state['selected_saved_job_index'] = index

# Callback to go back to the job list
def go_back_to_list():
    st.session_state['selected_saved_job_index'] = None

saved_jobs = fetch_saved_jobs()

if st.session_state['selected_saved_job_index'] is None:
    st.title("Saved Jobs")
    if saved_jobs:
        st.write(f"Found {len(saved_jobs)} saved job(s).")
        for i, job in enumerate(saved_jobs):
            job_card_html = f"""
            <div class="job-card">
                <h3>{job.get('TITLE', 'No Title')}</h3>
                <p><strong>Company:</strong> {job.get('COMPANY', 'Unknown')}</p>
                <p><strong>Location:</strong> {job.get('LOCATION', 'Unknown')}</p>
                <p><strong>Posted:</strong> {job.get('POSTED_DATE', 'Unknown')}</p>
                <p><strong>Status:</strong> {job.get('STATUS', 'Not Applied')}</p>
            </div>
            """
            st.markdown(job_card_html, unsafe_allow_html=True)
            st.button("View Details", key=f"view_details_{i}", on_click=select_job, args=(i,))
    else:
        st.info("No saved jobs found.")

    st.button("Logout", on_click=logout)

else:
    # Ensure the selected index is valid
    idx = st.session_state['selected_saved_job_index']
    if idx is not None and 0 <= idx < len(saved_jobs):
        selected_job = saved_jobs[idx]
        st.title("Job Details")
        st.write(f"**Job ID:** {selected_job.get('JOB_ID', 'Unknown')}")
        st.write(f"**Title:** {selected_job.get('TITLE', 'No Title')}")
        st.write(f"**Company:** {selected_job.get('COMPANY', 'Unknown')}")
        st.write(f"**Location:** {selected_job.get('LOCATION', 'Unknown')}")
        st.write(f"**Posted Date:** {selected_job.get('POSTED_DATE', 'Unknown')}")
        st.write(f"**Status:** {selected_job.get('STATUS', 'Not Applied')}")
        st.write(f"**Description:** {selected_job.get('DESCRIPTION', 'No Description')}")
        st.write(f"**Highlights:** {selected_job.get('JOB_HIGHLIGHTS', 'Unknown')}")
        st.write(f"**Feedback:** {selected_job.get('FEEDBACK', 'No Feedback Provided')}")
        st.write(f"**Created At:** {selected_job.get('CREATED_AT', 'Unknown')}")
        st.write(f"**Last Updated At:** {selected_job.get('UPDATED_AT', 'Not Updated')}")
        st.write(f"**Application Link:** {selected_job.get('APPLY_LINKS', '#')}")

        # Option to update status
        status_options = ["Not Applied", "Applied", "Interview Scheduled", "Offer Received", "Rejected"]
        current_status = selected_job.get('STATUS', 'Not Applied')
        if current_status not in status_options:
            current_status = "Not Applied"
        current_index = status_options.index(current_status)

        new_status = st.selectbox("Update Status", status_options, index=current_index)
        if st.button("Update Status"):
            response = update_job_status(selected_job.get('JOB_ID'), new_status, st.session_state['access_token'])
            if response.status_code == 200:
                st.success(f"Status updated to '{new_status}' successfully!")
                # After updating the status, re-fetch saved jobs and reset index
                saved_jobs = fetch_saved_jobs()
                st.session_state['selected_saved_job_index'] = None
            else:
                st.error(f"Failed to update status: {response.json().get('detail', 'Unknown error')}")

        # Option to delete the job
        if st.button("Delete Job"):
            response = delete_saved_job(selected_job.get('JOB_ID'), st.session_state['access_token'])
            if response.status_code == 200:
                st.success("Job deleted successfully!")
                # Refresh the job list after deletion
                saved_jobs = fetch_saved_jobs()
                st.session_state['selected_saved_job_index'] = None
            else:
                st.error(f"Failed to delete job: {response.json().get('detail', 'Unknown error')}")

        # Back button to return to the saved jobs list
        st.button("Back to Saved Jobs", on_click=go_back_to_list)

        # Logout button
        st.button("Logout", on_click=logout)
    else:
        # Invalid index: reset and show the job list again
        st.session_state['selected_saved_job_index'] = None
        st.error("Selected job index is invalid. Please select a job again.")
