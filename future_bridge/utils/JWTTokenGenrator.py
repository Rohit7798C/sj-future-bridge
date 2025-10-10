import os
import jwt

# Function to create JWT token
def create_jwt(payload):
    api_token = os.getenv("LMSTOKEN")
    # Define the header for the JWT
    header = {
    "alg": "HS256",
    "typ": "JWT"
}
    # Encode the header and payload to generate the JWT
    token = jwt.encode(payload, api_token, algorithm='HS256', headers=header)
    return token


def decode_jwt(token):
    try:
        # Get the secret key from the environment variable
        api_token = os.getenv("LMSTOKEN")
        
        # Decode the JWT token to get the payload (without verification, or with verification)
        payload = jwt.decode(token, api_token, algorithms=['HS256'], options={"verify_exp": True})
        print(payload)
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
