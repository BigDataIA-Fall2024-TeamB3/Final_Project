import streamlit as st
from utils import register_user, login_user

st.set_page_config(page_title="Login / Signup", layout="centered")

# Inject CSS and Font Awesome icons
st.markdown("""
<link rel="stylesheet" href="https://use.fontawesome.com/releases/v6.0.0/css/all.css" integrity="sha384-lZN37fQIK6L+Om5J0g+8vR5rbcLe+rfp81t0+uvQ6VZKfD0j2/o/o5ye9pYC/N39" crossorigin="anonymous">

<style>
/* Base styling relying on system theme */
body {
    font-family: "Helvetica Neue", Arial, sans-serif;
    margin: 0;
    padding: 0;
}

# /* Light mode */
# @media (prefers-color-scheme: light) {
#     body {
#         background: #F9F9F9;
#         color: #000000;
#     }
#     section.main > div {
#         background: #FFFFFF;
#         box-shadow: 0 4px 20px rgba(0,0,0,0.1);
#     }
#     input, .css-1cpxqw2, .stButton button {
#         color: #000000 !important;
#         border-color: #D1D5DB !important;
#     }
#     .stButton button {
#         background: #2563EB;
#         color: #FFFFFF !important;
#     }
#     .stButton button:hover {
#         background: #1E40AF;
#     }
# }

/* Dark mode */
@media (prefers-color-scheme: dark) {
    # body {
    #     background: #000000;
    #     color: #FFFFFF;
    # }
    # section.main > div {
    #     background: #111111;
    #     box-shadow: 0 4px 20px rgba(255,255,255,0.1);
    # }
    # input, .css-1cpxqw2 {
    #     color: #FFFFFF !important;
    #     border-color: #555 !important;
    #     background: #222222 !important;
    # }
    .stButton button {
        background: #2563EB;
        color: #FFFFFF !important;
        border: none;
    }
    .stButton button:hover {
        background: #1E40AF;
    }
}

/* Hide default Streamlit menu and footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Container styling */
section.main > div {
    padding: 3rem 2rem;
    border-radius: 12px;
    margin-top: 4rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
    transition: background 0.3s, color 0.3s;
}

/* Title styling */
h1, h2, h3, h4 {
    font-weight: 600;
    text-align: center;
    margin-bottom: 1rem;
}

/* Tabs styling */
[data-testid="stTabs"] button {
    font-weight: 500;
    font-size: 0.95rem;
}

/* Success and error messages */
.css-1m7wk2c {
    border-radius: 6px !important;
}

/* Spinner styling */
.css-6bx4c3 {
    margin-left: auto;
    margin-right: auto;
    display: block;
}

/* Center align the logout button */
#logout-button-container {
    text-align: center;
    margin-top: 1rem;
}

/* Footer */
.footer {
    text-align: center;
    font-size: 0.9rem;
    margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1><i class="fas fa-user-shield"></i> Login / Signup</h1>', unsafe_allow_html=True)

# Initialize session state
if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None

tab1, tab2 = st.tabs(["Login", "Signup"])

with tab1:
    st.markdown('### <i class="fas fa-sign-in-alt"></i> Login', unsafe_allow_html=True)
    login_username = st.text_input("Username", key="login_username", placeholder="Enter your username")
    login_password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
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

    if st.session_state['access_token'] is not None:
        st.markdown('<div id="logout-button-container">', unsafe_allow_html=True)
        if st.button("Logout"):
            st.session_state['access_token'] = None
            st.success("Logged out successfully!")
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('### <i class="fas fa-user-plus"></i> Signup', unsafe_allow_html=True)
    signup_username = st.text_input("Username", key="signup_username", placeholder="Create a unique username")
    signup_email = st.text_input("Email", key="signup_email", placeholder="Enter your email address")
    signup_password = st.text_input("Password", type="password", key="signup_password", placeholder="Create a password")
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


# Footer with all rights reserved
st.markdown('<div class="footer">© 2024. All rights reserved.</div>', unsafe_allow_html=True)
