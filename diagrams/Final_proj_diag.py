from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.custom import Custom
from diagrams.programming.framework import FastAPI
from diagrams.onprem.container import Docker
from diagrams.gcp.compute import GCE
from diagrams.aws.storage import S3

# Paths to custom icons
streamlit_icon = "streamlit_icon.png"
openai_icon = "openai_icon.png"
docker_icon = "docker_icon.png"
fastapi_icon = "fastapi_icon.png"
airflow_icon = "airflow_icon.png"
snowflake_icon = "snowflake_icon.png"
serp_icon = "serp_icon.png"
google_jobs_icon = "google_jobs_icon.png"
langgraph_icon = "langgraph_icon.png"

# Diagram layout attributes
graph_attr = {
    "fontsize": "15",
    "splines": "ortho",
    "rankdir": "LR",
    "compound": "true"
}

edge_attr = {
    "color": "black",
}

# Node attributes for larger icons
large_node_attr = {
    "imagescale": "true",
    "width": "3",
    "height": "3"
}

user_storage_graph_attr = {
    "rankdir": "LR",  # Force left-to-right layout
    "splines": "ortho"
}

# Create the main diagram
with Diagram("Job Assistant Architecture", show=True, graph_attr=graph_attr, edge_attr=edge_attr):
    # Data Ingestion Layer
    with Cluster("Data Ingestion Layer"):
        google_jobs = Custom("Google Jobs", google_jobs_icon)
        serp_api = Custom("SERP API", serp_icon)
        airflow = Custom("Airflow", airflow_icon)
        
        google_jobs >> serp_api >> airflow

    # Storage Layer
    with Cluster("Storage Layer"):
        snowflake = Custom("Snowflake", snowflake_icon)
        airflow >> snowflake

    # Frontend Layer
    with Cluster("Frontend Layer"):
        user = User("End User")
        streamlit = Custom("Streamlit", streamlit_icon)
        
    with Cluster("User storage", graph_attr=user_storage_graph_attr):
        aws_bucket = S3("AWS S3 Bucket")
        snowflake1 = Custom("Snowflake", snowflake_icon)

    # Processing & Backend Layer
    with Cluster("Processing & Backend Layer"):
        with Cluster("Docker Deployment", graph_attr={"labeljust": "r"}):
            docker_compose = Custom("Docker Compose", docker_icon)
            docker_fastapi = Custom("FastAPI Container", docker_icon)
            docker_streamlit = Custom("Streamlit Container", docker_icon)
            gcp_vm = GCE("GCP VM")
            
            [docker_fastapi, docker_streamlit] >> docker_compose >> gcp_vm

        fastapi = Custom("FastAPI", fastapi_icon)
        langgraph = Custom("SQL Agent", langgraph_icon, **large_node_attr)
        openai = Custom("OpenAI API", openai_icon)
        openai1 = Custom("OpenAI API", openai_icon)

        # Processing connections
        fastapi >> docker_fastapi
#         fastapi >> snowflake1
        langgraph >> Edge(color="black") >> snowflake
        snowflake >> Edge(color="black") >> langgraph
        
        # Bidirectional connections
        fastapi >> Edge(color="black") >> langgraph
        langgraph >> Edge(color="black") >> openai
        openai >> Edge(color="black") >> langgraph
        langgraph >> Edge(color="black") >> fastapi
        
        fastapi >> Edge(color="black") >> aws_bucket
        aws_bucket >> Edge(color="black") >> fastapi
        fastapi >> Edge(color="black") >> openai1
        openai1 >> Edge(color="black") >> fastapi
        
        fastapi >> Edge(color="black") >> snowflake
        snowflake >> Edge(color="black") >> fastapi

    # Frontend connections
    user >> streamlit
    streamlit >> docker_streamlit
    fastapi >> streamlit
    streamlit >> Edge(color="black") >> fastapi