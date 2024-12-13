import streamlit as st
from utils import get_saved_jobs, update_job_status, delete_saved_job, generate_feedback, save_feedback, chat_feedback

st.set_page_config(page_title="Saved Jobs", layout="centered")

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
    color: #000000;
    font-size: 0.95rem;
}

.job-details-value {
    display: block;
    margin-bottom: 1rem;
    word-wrap: break-word;
    font-size: 0.95rem;
    color: #000000;
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
    color: 000000;
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
if 'feedback' not in st.session_state:
    st.session_state['feedback'] = ""

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
    st.session_state['feedback'] = ""

# Callback to go back to the job list
def go_back_to_list():
    st.session_state['selected_saved_job_index'] = None
    st.session_state['feedback'] = ""

# Fetch the saved jobs
saved_jobs = fetch_saved_jobs()

if st.session_state['selected_saved_job_index'] is None:
    # Display the list of saved jobs
    st.title("Saved Jobs")
    st.markdown("---")
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

    st.markdown("---")
    st.button("Logout", on_click=logout)
    st.markdown('<div class="footer">© 2024. All rights reserved.</div>', unsafe_allow_html=True)

else:
    idx = st.session_state['selected_saved_job_index']
    if idx is not None and 0 <= idx < len(saved_jobs):
        selected_job = saved_jobs[idx]
        st.title(f"Job Details: {selected_job.get('TITLE', 'No Title')}")
        st.markdown("---")
        # Tabs for different operations
        tab1, tab2, tab3, tab4 = st.tabs(["Job Details", "Feedback", "Update Status", "Delete Job"])

        with tab1:
            st.subheader("Job Details")
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
            st.subheader("Detailed Feedback For the Job")

            # Explanation of what "Generate Feedback" does
            st.write(
                """
                Click **"Generate Feedback"** to receive comprehensive insights and suggestions based on the job's description and highlights.
                This feedback is tailored to help you refine your **resume** and **cover letter**, ensuring they align closely with the role's requirements.
                
                For example, the generated feedback might point out how you can emphasize certain skills in your resume, or suggest ways to highlight relevant experiences in your cover letter that directly address the job description.
                """
            )

            # Generate general feedback
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
                        st.session_state['feedback'] = response.json().get('feedback', 'No feedback available.')
                        st.write(st.session_state['feedback'])
                    else:
                        st.error(f"Failed to generate feedback: {response.json().get('detail', 'Unknown error')}")

            if st.session_state['feedback']:
                if st.button("Save Feedback"):
                    save_response = save_feedback(
                        job_id=selected_job.get('JOB_ID', 'Unknown'),
                        feedback=st.session_state['feedback'],
                        token=st.session_state['access_token']
                    )
                    if save_response.status_code == 200:
                        st.success("Feedback saved successfully!")
                    else:
                        st.error(f"Failed to save feedback: {save_response.json().get('detail', 'Unknown error')}")

            st.markdown("---")
            st.subheader("Ask Specific Questions")

            # Explanation for the "Ask Specific Questions" section
            st.write(
                """
                Use the section below to ask targeted questions about this job and how it relates to your **resume** or **cover letter**.
                
                **Instructions:**
                1. Select whether you want to focus on your **Resume** or **Cover Letter**.
                2. Enter a specific question that relates to the job, the job description, or how your selected document (resume/cover letter) can be improved for this particular role.
                
                This tailored response can help you fine-tune your application materials to better match what the employer is looking for.
                """
            )

            # User can choose document type
            document_type = st.selectbox("Select Document", ["Resume", "Cover_Letter"])
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

                # Explanation of the Update Status feature
                st.write(
                    """
                    Keep track of your application progress by updating the job’s status. 
                    This helps you stay organized and clearly see where you stand in the hiring process.
                    
                    **Status Options:**
                    - **Not Applied:** You have saved the job but have not yet submitted an application.
                    - **Applied:** You have submitted your application and are waiting to hear back.
                    - **Interview Scheduled:** You have been invited to an interview for this role.
                    - **Offer Received:** You have received a job offer for this position.
                    - **Rejected:** Your application was not selected for further consideration.
                    
                    Select the appropriate status below and click **"Update Status"** to reflect the current stage of your application.
                    """
                )

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

                # Explanation of the Delete Job feature
                st.write(
                    """
                    If you no longer wish to keep track of this position, you can remove it from your saved jobs list. 
                    Deleting a job from your saved list means you will no longer see it or any associated feedback or status updates for this position.

                    **Note:**  
                    This action is permanent and cannot be undone. Make sure you no longer need this job in your records before proceeding.
                    """
                )

                if st.button("Delete Job"):
                    response = delete_saved_job(selected_job.get('JOB_ID'), st.session_state['access_token'])
                    if response.status_code == 200:
                        st.success("Job deleted successfully!")
                        saved_jobs = fetch_saved_jobs()
                        st.session_state['selected_saved_job_index'] = None
                    else:
                        st.error(f"Failed to delete job: {response.json().get('detail', 'Unknown error')}")


        st.markdown("---")
        st.button("Back to Saved Jobs", on_click=go_back_to_list)
        st.button("Logout", on_click=logout)
    else:
        st.session_state['selected_saved_job_index'] = None
        st.error("Selected job index is invalid. Please select a job again.")
