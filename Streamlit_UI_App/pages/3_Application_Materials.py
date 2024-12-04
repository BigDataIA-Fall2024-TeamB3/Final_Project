import streamlit as st
import time
from utils import update_files, get_current_user

st.set_page_config(page_title="Update Files", layout="centered")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None

def logout():
    st.session_state['access_token'] = None

# Place the logout button at the top so its action is processed first
if st.session_state['access_token'] is not None:
    # Using on_click ensures the state is updated immediately before rendering continues
    st.button("Logout", on_click=logout)
    if st.session_state['access_token'] is None:
        st.success("Logged out successfully!")
        st.stop()
else:
    st.warning("You need to log in to update your files.")
    st.stop()

st.title("Update Files")

def display_pdf_links(resume_link, cover_letter_link):
    timestamp = int(time.time())  # For cache-busting
    if resume_link:
        st.markdown("**Current Resume:**")
        st.markdown(
            f'<iframe src="{resume_link}?_={timestamp}" width="700" height="900"></iframe>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No resume on record. Please upload one.")

    if cover_letter_link:
        st.markdown("**Current Cover Letter:**")
        st.markdown(
            f'<iframe src="{cover_letter_link}?_={timestamp}" width="700" height="900"></iframe>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No cover letter on record. Please upload one.")

resume_file = st.file_uploader("Upload New Resume (PDF)", type=["pdf"], key="update_resume_file")
cover_letter_file = st.file_uploader("Upload New Cover Letter (PDF)", type=["pdf"], key="update_cover_letter_file")
update_button = st.button("Update Files")

if update_button:
    if resume_file is None and cover_letter_file is None:
        st.error("Please upload at least one file to update.")
    else:
        with st.spinner("Updating files..."):
            response = update_files(resume_file, cover_letter_file, st.session_state['access_token'])
            if response.status_code == 200:
                st.success("Files updated successfully!")
                updated_user = get_current_user(st.session_state['access_token'])
                if updated_user:
                    display_pdf_links(updated_user.get('resume_link'), updated_user.get('cover_letter_link'))
                else:
                    st.error("Could not fetch updated details. Please refresh.")
            else:
                st.error("Failed to update files. Please try again.")
else:
    # Just display current PDFs
    user = get_current_user(st.session_state['access_token'])
    if not user:
        st.error("Could not fetch user details. Please log in again.")
        st.stop()

    st.write("Below are your current resume and cover letter on record:")
    display_pdf_links(user.get('resume_link'), user.get('cover_letter_link'))
