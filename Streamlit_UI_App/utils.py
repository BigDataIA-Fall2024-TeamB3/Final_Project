import streamlit as st
import requests
import os

API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")

def register_user(username, email, password, resume_file, cover_letter_file):
    url = f"{API_BASE_URL}/register"
    files = {
        'resume': resume_file,
        'cover_letter': cover_letter_file
    }
    data = {
        'username': username,
        'email': email,
        'password': password
    }
    response = requests.post(url, data=data, files=files)
    return response

def login_user(username, password):
    url = f"{API_BASE_URL}/login"
    data = {
        'username': username,
        'password': password
    }
    response = requests.post(url, data=data)
    return response

def get_current_user(token):
    url = f"{API_BASE_URL}/users/me"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None  # Return None if not successful

def search_jobs(query, token):
    url = f"{API_BASE_URL}/search/jobs"
    headers = {'Authorization': f'Bearer {token}'}
    params = {'query': query}
    response = requests.get(url, headers=headers, params=params)
    return response

def update_files(resume_file, cover_letter_file, token):
    url = f"{API_BASE_URL}/users/me/files"
    headers = {'Authorization': f'Bearer {token}'}
    files = {}
    if resume_file is not None:
        files['resume'] = resume_file
    if cover_letter_file is not None:
        files['cover_letter'] = cover_letter_file
    response = requests.put(url, headers=headers, files=files)
    return response
