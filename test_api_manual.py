import requests

# Test login
response = requests.post(
    'http://localhost:8000/login',
    headers={
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    },
    data={
        'grant_type': '',
        'username': 'admin@example.com',
        'password': 'admin',
        'scope': '',
        'client_id': '',
        'client_secret': ''
    }
)

print(f'Login Status: {response.status_code}')
if response.status_code == 200:
    token = response.json()['access_token']
    print(f'Token obtenido: {token[:20]}...')
    
    # Test predict
    with open('tests/dog.jpeg', 'rb') as f:
        files = {'file': ('dog.jpeg', f, 'image/jpeg')}
        headers = {'Authorization': f'Bearer {token}'}
        
        predict_response = requests.post(
            'http://localhost:8000/model/predict',
            headers=headers,
            files=files
        )
    
    print(f'\nPredict Status: {predict_response.status_code}')
    if predict_response.status_code == 200:
        data = predict_response.json()
        print(f'Response: {data}')
    else:
        print(f'Error: {predict_response.text}')
else:
    print(f'Error: {response.text}')
