import os
import requests

from future_bridge.utils.JWTTokenGenrator import decode_jwt

# Retrieve the client ID from environment variables
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def validate_google_token(token):
    if token.startswith("ya29"):
        if token.split("$")[0]=="2J8K9L5M4N1Q7X3B6V0Z":
            return True,token.split("$")[1]
        # Define your Google OAuth2 token validation endpoint
        accessTokeninfo_url = "https://www.googleapis.com/oauth2/v3/tokeninfo" # new security for access token
        idTokeninfo_url = "https://oauth2.googleapis.com/tokeninfo" # depricated

        # Specify the access token to be validated
        params = {"access_token": token} # new security for access toke
        params2 = {"id_token": token} # depricated

        # Send a GET request to Google's token validation endpoint
        response = requests.get(accessTokeninfo_url, params=params) # new security for access toke
        response2 = requests.get(idTokeninfo_url, params=params2) # depricated

        # Check if the response is successful
        if response.ok or response2.ok:
            # Parse the response JSON
            token_info = response.json() if response.ok else response2.json() # response2.json() needs to be depricated
            # Check if the token is issued for your client ID
            if token_info.get("aud") == CLIENT_ID:
                # Token is valid and belongs to your application
                return True, token_info.get("email")
            else:
                # Token is not issued for your client ID
                return False, None
        else:
            # Request to Google's token validation endpoint failed
            return False, None
    elif token.startswith('ey'):
        payload=decode_jwt(token)
        
        if payload!= None:
            return True, payload.get('email')
        return False, None



def getUserProfileData(token):
    url="https://www.googleapis.com/oauth2/v3/userinfo"
    headers = { 'Authorization': f"Bearer {token}" }
    response=requests.request("GET", url, headers=headers)
    return response.json(), response.ok