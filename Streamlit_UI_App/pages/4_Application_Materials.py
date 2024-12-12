import streamlit as st
import time
from utils import update_files, get_current_user

st.set_page_config(page_title="Application Materials", layout="centered")

# Custom CSS for styling without text or font color modifications
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

body {
    background-color: var(--primary-background-color);
    font-family: "Helvetica Neue", Arial, sans-serif;
    margin: 0;
    padding: 0;
}
section.main > div {
    background: var(--secondary-background-color);
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
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

/* Info, success, error messages */
.css-1m7wk2c, .element-container {
    border-radius: 6px !important;
}

/* Buttons styling */
.stButton button {
    background: #2563EB;
    color: #FFFFFF !important;
    border: none;
    border-radius: 6px;
    padding: 0.75rem 1.25rem;
    font-size: 0.95rem;
    transition: background 0.3s;
    margin-top: 1rem;
}

.stButton button:hover {
    background: #1E40AF;
    cursor: pointer;
}

/* File uploader styling */
.css-1cpxqw2 {
    border: 1px solid #D1D5DB !important;
    border-radius: 6px !important;
    font-size: 0.9rem;
}

/* PDF viewer section */
.pdf-section {
    margin-top: 1.5rem;
}
.pdf-container {
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
    justify-content: center;
}
.pdf-tile {
    flex: 1 1 300px;
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    min-width: 300px;
}
.pdf-tile iframe {
    width: 100%;
    height: 500px;
    border: none;
    border-radius: 6px;
}

/* Separator */
hr {
    border: none;
    border-top: 1px solid #E5E7EB;
    margin: 2rem 0;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None

def logout():
    st.session_state['access_token'] = None

if st.session_state['access_token'] is None:
    st.warning("You need to log in to update your files.")
    st.stop()

st.title("Your Application Materials")
st.markdown("---")
user = get_current_user(st.session_state['access_token'])
if not user:
    st.error("Could not fetch user details. Please log in again.")
    st.stop()

def display_pdf_links(resume_link, cover_letter_link):
    timestamp = int(time.time())  # For cache-busting

    pdf_tiles = []
    if resume_link:
        pdf_tiles.append((resume_link, "Current Resume"))
    else:
        st.info("No resume on record. Please upload one.")

    if cover_letter_link:
        pdf_tiles.append((cover_letter_link, "Current Cover Letter"))
    else:
        st.info("No cover letter on record. Please upload one.")

    if pdf_tiles:
        st.markdown('<div class="pdf-container">', unsafe_allow_html=True)
        for link, title in pdf_tiles:
            st.markdown(f'<div class="pdf-tile"><h4>{title}</h4><iframe src="{link}?_={timestamp}"></iframe></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

display_pdf_links(user.get('resume_link'), user.get('cover_letter_link'))

st.markdown("---")
st.subheader("Upload Updated Documents")
st.write("Select new files below to update your existing application materials. If you upload only one type of document (e.g., just a new resume), only that document will be updated.")

resume_file = st.file_uploader("Upload a New Resume (PDF)", type=["pdf"], key="update_resume_file")
cover_letter_file = st.file_uploader("Upload a New Cover Letter (PDF)", type=["pdf"], key="update_cover_letter_file")
update_button = st.button("Update Files")

if update_button:
    if resume_file is None and cover_letter_file is None:
        st.error("Please upload at least one file to update.")
    else:
        with st.spinner("Updating your files..."):
            response = update_files(resume_file, cover_letter_file, st.session_state['access_token'])
            if response.status_code == 200:
                st.success("Your files have been successfully updated!")
                updated_user = get_current_user(st.session_state['access_token'])
                if updated_user:
                    st.markdown("---")
                    display_pdf_links(updated_user.get('resume_link'), updated_user.get('cover_letter_link'))
                else:
                    st.error("Could not fetch updated details. Please refresh.")
            else:
                st.error("Failed to update files. Please try again.")

st.markdown("---")
st.button("Logout", on_click=logout)
if st.session_state['access_token'] is None:
    st.success("Logged out successfully!")
    st.stop()
