# Intelligent Job Search Assistant

## Members:
- **Viswanath Raju Indukuri**
- **Snehal Shivaji Molavade**
- **Sai Vivekanand Reddy Vangala**

---

## Architecture

The project leverages a multi-layered architecture with the following technologies:
- **Backend**: FastAPI for handling APIs and integrating with LLMs.
- **Frontend**: Streamlit for user interaction and visualizations.
- **Database**: Snowflake for storing user and job data.
- **Storage**: AWS S3 for managing uploaded files (resumes and cover letters).
- **Data Scraping**: Google SERP API for fetching job listings.
- **Analytics**: Descriptive and visual insights using integrated modules.
- **Deployment**: Dockerized application with CI/CD via GitHub Actions and hosting on GCloud VM.

![Architecture Diagram](diagrams/job_assistant_architecture.png)  

---

## Data and Application Workflow

```mermaid
graph TD
    %% Data Flow %%
    subgraph Data Flow
        A[Google Jobs Scraping via Google SERP API] --> B[Preprocessing and Transformations]
        B --> C[Airflow] --> Cd[Load Data into Snowflake Database]
    end

    %% Application Flow and Back%%
    subgraph Application Flow
        Login_Signup --> D[Login or Signup]
        D -->|Signup| E[Save User Details to Snowflake Users Database, Resume and Cover Letter to S3]
        D -->|Login| G[Authenticate with JWT Token]
        
        G --> H[User Logged In]
        
        H --> I[User Asks for Jobs in Natural Language]
        I --> J[SQL Agent Writes SQL Query in the Backend]
        J --> K[Retrieve Jobs Data from Snowflake Job Listings Database]
        K --> L[Display Job Listings Data to User]
        L --> R[Set Job Status as Applied]

        L --> M[User Selects Particular Job to Save]
        M --> N[Saves Selected Job Details in Snowflake Saved Jobs DB]

        H --> OO[View Saved Jobs from Snowflake Saved Jobs DB]
        OO --> FF[Set Job Status as Applied]
        OO --> GG[Check Relevance with Profile and save the feedback and Job Details in Snowflake Results DB]

        L --> P[Check Selected Job Relevance with Profile]
        P --> PQ[Sends Job description Along with Resume and Cover Letter to OpenAI for Structured Feedaback]
        PQ --> Q[Save Feedback and Job Details in Snowflake Results DB]

        R --> S[Save Status in Snowflake Results DB]

        H --> T[Analytics Option]
        T --> U[Analytics for the applied jobs from Snowflake Results DB]
    end
```
---

## Links

1. **Codelabs Report**: [View Report](https://codelabs-preview.appspot.com/?file_id=1JGeUAieHgwrS8Kxsetu1_HHAeJsj8REv8EMC-kxBqW0#0)
2. **Proposal Video**: [Watch Video](https://drive.google.com/drive/folders/1DHzRlApDj-2Uo6RVT5viC4lYyjXmdB3s?usp=sharing)

