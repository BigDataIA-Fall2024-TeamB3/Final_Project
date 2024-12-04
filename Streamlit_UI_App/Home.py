import streamlit as st

# Set page config
st.set_page_config(page_title="Job Portal", layout="centered")

# Hide the default Streamlit menu and footer
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Page Title
st.title("Job Portal")

# Introductory text
st.write("Welcome to the Job Portal Streamlit App.")
st.write("This platform helps you find and apply for your next job opportunity, manage your professional documents, and streamline your application process.")

# Instructions
st.write("**Instructions:**")
st.write("- Use the sidebar to navigate through the application.")
st.write("- Go to the **Login / Signup** page to access or create your account.")
st.write("- Once logged in, you can **Search for Jobs**, **Update your Files**, and manage your profile.")

st.write("We hope you find the perfect role through our platform!")
