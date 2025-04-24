import requests 
import json
import os

# Assemble the URL for the API call 

api_url = "https://cad.onshape.com/documents/7820391e3a9b37485d78da07"

# Optional query parameters can be assigned 
params = {}

# Use the keys from the developer portal
access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_KEY")

# Define the header for the request 
headers = {'Accept': 'application/json;charset=UTF-8;qs=0.09',
           'Content-Type': 'application/json'}

# Putting everything together to make the API request 
response = requests.get(api_url, 
                        params=params, 
                        auth=(access_key, secret_key),
                        headers=headers)

# --- Debugging ---
print(f"Status Code: {response.status_code}")
print("Response Headers:")
print(response.headers)
print("Response Text:")
print(response.text) # Print the raw text content
# --- End Debugging ---

# Check if the request was successful before trying to parse JSON
if response.ok: # Checks if status_code is less than 400
    try:
        # Convert the response to formatted JSON and print the `name` property
        print(json.dumps(response.json(), indent=4))
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON, even though status code was OK.")
else:
    print(f"Error: Request failed with status code {response.status_code}")


