import streamlit as st

# Set page config (include a favicon and a custom layout)
st.set_page_config(
    page_title="Intelligent Job Search Assistant",
    page_icon=":briefcase:",
    layout="wide"
)

# Custom CSS for black text and light background
st.markdown("""
<style>
body {
    background-color: #F9F9F9;
    font-family: "Helvetica Neue", Arial, sans-serif;
    color: #000000; /* Ensure text is black */
}
section.main > div {
    background: #FFFFFF; 
    padding: 2rem; 
    border-radius: 8px; 
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-top: 2rem;
}
</style>
""", unsafe_allow_html=True)

# Load header image from directory (uncomment if image is available)
# st.image("../icon.webp", use_column_width=True)

# Page Title with a catchy tagline
st.title("Intelligent Job Search Assistant")
st.markdown("### **Discover Your Next Opportunity with Ease**")

st.write(
    """
    Our Intelligent Job Search Assistant is designed to streamline your journey towards finding the perfect job. 
    From tailored recommendations to intelligent feedback, we simplify the process so you can focus on what matters most: 
    advancing your career.

    **Key Highlights:**
    - **Personalized Searches:** Get job listings aligned with your skills and preferences.
    - **Document Management:** Upload, edit, and store your resumes and cover letters securely.
    - **Smart Tracking:** Keep track of saved jobs, application statuses, and deadlines in one place.
    - **AI-Driven Feedback:** Enhance your applications with real-time resume and cover letter feedback.
    - **Actionable Insights:** Use analytics to refine your strategy and increase your success rate.

    Whether you’re an experienced professional or just starting out, our assistant is designed to help you stand out from the crowd.
    """
)

# Additional instructions and steps
st.markdown("---")
st.subheader("How to Get Started")
st.write(
    """
    1. **Login / Signup**: Access your account or create a new one to unlock all features.
    2. **Explore Job Listings**: Use the advanced search to find positions that fit your profile.
    3. **Manage Your Documents**: Upload and refine your resumes and cover letters.
    4. **Track Your Saved Jobs**: Keep an organized list of interesting roles and follow their status.
    5. **Leverage Analytics**: View insightful analytics to understand your progress and improve your approach.
    """
)

st.markdown("---")
st.markdown(
    """
    ### 🌟 **Take the Next Step in Your Career**  
    Turn your ambitions into action. Start using our Intelligent Job Search Assistant today!
    """
)

# Footer with all rights reserved
st.markdown('<div class="footer">© 2024. All rights reserved.</div>', unsafe_allow_html=True)