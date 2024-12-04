import streamlit as st
from utils import register_user, login_user

st.set_page_config(page_title="Login / Signup", layout="centered")

# Hide default Streamlit menu and footer if desired
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Login / Signup")

# Initialize session state
if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None

tab1, tab2 = st.tabs(["Login", "Signup"])

with tab1:
    st.subheader("Login")
    login_username = st.text_input("Username", key="login_username")
    login_password = st.text_input("Password", type="password", key="login_password")
    login_button = st.button("Login")

    if login_button:
        with st.spinner("Logging in..."):
            response = login_user(login_username, login_password)
            if response.status_code == 200:
                data = response.json()
                st.session_state['access_token'] = data['access_token']
                st.success("Logged in successfully!")
            else:
                st.error("Login failed. Check your username and password.")

with tab2:
    st.subheader("Signup")
    signup_username = st.text_input("Username", key="signup_username")
    signup_email = st.text_input("Email", key="signup_email")
    signup_password = st.text_input("Password", type="password", key="signup_password")
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], key="resume_file")
    cover_letter_file = st.file_uploader("Upload Cover Letter (PDF)", type=["pdf"], key="cover_letter_file")
    signup_button = st.button("Signup")

    if signup_button:
        if resume_file is None or cover_letter_file is None:
            st.error("Please upload both resume and cover letter.")
        else:
            with st.spinner("Signing up..."):
                response = register_user(signup_username, signup_email, signup_password, resume_file, cover_letter_file)
                if response.status_code == 200:
                    st.success("Signup successful! You can now log in.")
                else:
                    error_detail = response.json().get('detail', 'Signup failed.')
                    st.error(f"Signup failed: {error_detail}")

# Add logout button if logged in
if st.session_state['access_token'] is not None:
    if st.button("Logout"):
        st.session_state['access_token'] = None
        st.success("Logged out successfully!")
