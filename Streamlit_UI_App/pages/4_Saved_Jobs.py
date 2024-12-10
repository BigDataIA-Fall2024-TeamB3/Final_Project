import streamlit as st
from utils import get_saved_jobs, update_job_status, delete_saved_job, generate_feedback, save_feedback, chat_feedback

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

# Logout function
def logout():
    st.session_state['access_token'] = None
    st.session_state['selected_saved_job_index'] = None
    st.success("Logged out successfully!")

# Fetch saved jobs
def fetch_saved_jobs():
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

# Fetch the saved jobs
saved_jobs = fetch_saved_jobs()

if st.session_state['selected_saved_job_index'] is None:
    # Display the list of saved jobs
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
    idx = st.session_state['selected_saved_job_index']
    if idx is not None and 0 <= idx < len(saved_jobs):
        selected_job = saved_jobs[idx]
        st.title(f"Job Details: {selected_job.get('TITLE', 'No Title')}")

        # Tabs for different operations
        tab1, tab2, tab3, tab4 = st.tabs(["Job Details", "Feedback", "Update Status", "Delete Job"])

        with tab1:
            st.title("Job Details")
            st.write(f"**Job ID:** {selected_job.get('JOB_ID', 'Unknown')}")
            st.write(f"**Title:** {selected_job.get('TITLE', 'No Title')}")
            st.write(f"**Company:** {selected_job.get('COMPANY', 'Unknown')}")
            st.write(f"**Location:** {selected_job.get('LOCATION', 'Unknown')}")
            st.write(f"**Posted Date:** {selected_job.get('POSTED_DATE', 'Unknown')}")
            st.write(f"**Status:** {selected_job.get('STATUS', 'Not Applied')}")
            st.write(f"**Description:** {selected_job.get('DESCRIPTION', 'No Description')}")
            st.write(f"**Highlights:** {selected_job.get('JOB_HIGHLIGHTS', 'Unknown')}")
            st.write(f"**Feedback:** {selected_job.get('FEEDBACK', 'Unknown')}")
            st.write(f"**Apply Here:** {selected_job.get('APPLY_LINKS', 'Unknown')}")
            st.write(f"**Created At:** {selected_job.get('CREATED_AT', 'Unknown')}")
            st.write(f"**Updated At:** {selected_job.get('UPDATED_AT', 'Unknown')}")

        with tab2:
            st.subheader("Feedback")

            # Generate general feedback
            feedback = st.session_state.get("feedback", "")
            feedback_button = st.button("Generate Feedback")
            if feedback_button:
                with st.spinner("Generating feedback..."):
                    response = generate_feedback(
                        job_id=selected_job.get('JOB_ID', 'Unknown'),
                        description=selected_job.get('DESCRIPTION', ''),
                        highlights=selected_job.get('JOB_HIGHLIGHTS', ''),
                        token=st.session_state['access_token']
                    )
                    if response.status_code == 200:
                        feedback = response.json().get('feedback', 'No feedback available.')
                        st.session_state['feedback'] = feedback
                        st.write(feedback)
                    else:
                        st.error(f"Failed to generate feedback: {response.json().get('detail', 'Unknown error')}")

            if feedback:
                if st.button("Save Feedback"):
                    save_response = save_feedback(
                        job_id=selected_job.get('JOB_ID', 'Unknown'),
                        feedback=feedback,
                        token=st.session_state['access_token']
                    )
                    if save_response.status_code == 200:
                        st.success("Feedback saved successfully!")
                    else:
                        st.error(f"Failed to save feedback: {save_response.json().get('detail', 'Unknown error')}")

            st.markdown("---")
            st.subheader("Ask Specific Questions")

            # User can choose document type
            document_type = st.selectbox("Select Document", ["Resume", "Cover Letter"])
            question = st.text_area("Ask a specific question")

            if st.button("Get Specific Feedback"):
                if not question.strip():
                    st.error("Please enter a question.")
                else:
                    with st.spinner("Getting specific feedback..."):
                        chat_response = chat_feedback(
                            document_type=document_type.lower(),
                            question=question,
                            description=selected_job.get('DESCRIPTION', ''),
                            highlights=selected_job.get('JOB_HIGHLIGHTS', ''),
                            token=st.session_state['access_token']
                        )
                        if chat_response.status_code == 200:
                            response_text = chat_response.json().get("response", "No response available.")
                            st.write(response_text)
                        else:
                            st.error(f"Failed to get feedback: {chat_response.json().get('detail', 'Unknown error')}")

        with tab3:
            st.subheader("Update Status")
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
                    saved_jobs = fetch_saved_jobs()
                    st.session_state['selected_saved_job_index'] = None
                else:
                    st.error(f"Failed to update status: {response.json().get('detail', 'Unknown error')}")

        with tab4:
            st.subheader("Delete Job")
            if st.button("Delete Job"):
                response = delete_saved_job(selected_job.get('JOB_ID'), st.session_state['access_token'])
                if response.status_code == 200:
                    st.success("Job deleted successfully!")
                    saved_jobs = fetch_saved_jobs()
                    st.session_state['selected_saved_job_index'] = None
                else:
                    st.error(f"Failed to delete job: {response.json().get('detail', 'Unknown error')}")

        st.button("Back to Saved Jobs", on_click=go_back_to_list)
        st.button("Logout", on_click=logout)
    else:
        st.session_state['selected_saved_job_index'] = None
        st.error("Selected job index is invalid. Please select a job again.")
