from flask_jwt_extended import decode_token

def get_user_id_from_token(token):
    decoded_token = decode_token(token)
    return decoded_token['sub']
