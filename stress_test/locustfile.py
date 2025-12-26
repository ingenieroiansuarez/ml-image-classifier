from typing import Optional

import requests
from locust import HttpUser, between, task

API_BASE_URL = "http://localhost:8000"


def login(username: str, password: str) -> Optional[str]:
    """This function calls the login endpoint of the API to authenticate the user and get a token.

    Args:
        username (str): email of the user
        password (str): password of the user

    Returns:
        Optional[str]: token if login is successful, None otherwise
    """
    # TODO: Implement the login function
    # 1 - make a request to the login endpoint
    # 2 - check if the response status code is 200
    # 3 - if it is, return the access_token
    # 4 - if it is not, return None
    url = f"{API_BASE_URL}/login"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "",
        "username": username,
        "password": password,
        "scope": "",
        "client_id": "",
        "client_secret": "",
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        return None


class APIUser(HttpUser):
    wait_time = between(1, 5)

    # Put your stress tests here.
    # See https://docs.locust.io/en/stable/writing-a-locustfile.html for help.
    # TODO
    # raise NotImplementedError
    
    def on_start(self):
        """Login once when the user starts"""
        self.token = login("admin@example.com", "admin")
    
    @task(3)
    def test_predict(self):
        """Test the predict endpoint with an image"""
        if self.token:
            with open("dog.jpeg", "rb") as image_file:
                files = {"file": ("dog.jpeg", image_file, "image/jpeg")}
                headers = {"Authorization": f"Bearer {self.token}"}
                self.client.post(
                    "/model/predict",
                    headers=headers,
                    files=files,
                    name="/model/predict"
                )
    
    @task(1)
    def test_index(self):
        """Test the docs endpoint (index)"""
        self.client.get("/docs", name="/docs")
