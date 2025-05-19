from flask import current_app
from datetime import timedelta
import base64
import string
import random
import os

from .db import get_db_connection

def get_jupyterhub_secret_key():
    return current_app.config["JUPYTERHUB_SECRET_KEY"]

def get_decrypt_secret_key():
    return current_app.config["DECRYPT_SECRET_KEY"]

def get_allowed_extensions():
    return current_app.config["ALLOWED_EXTENSIONS"]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()

def get_node_admin_tokens(node:str):
    return current_app.config["NODE_ADMIN_TOKENS"][f"{node}"]
                              
def get_external_service_urls(course_name:str):
    return current_app.config["EXTERNAL_SERVICE_URLS"][f"{course_name}"]

def get_machine():
    return current_app.config["machines"]

def get_system_user():
    return current_app.config["system_user"]

def get_testsecter_admin():
    return current_app.config["testsecter_admin"]

def get_max_content_length():
    return current_app.config["MAX_CONTENT_LENGTH"]

def get_dataset_folder():
    return current_app.config["DATASETS_FOLDER"]

def get_upload_folder():
    return current_app.config["UPLOAD_FOLDER"]

def get_trinetra_url():
    return current_app.config["TRINETRA_URL"]

def get_publish_machines():
    return current_app.config["publish_machines"]

def get_clustermonitor_url():
    return current_app.config["CLUSTER_MONITOR_PATH"]

def get_dataset_url():
    return current_app.config["DATASET_PATH"]

async def encrypt(text):
    """Encrypt text using XOR and base64 encoding."""
    try:
        secret_key = get_decrypt_secret_key()
        encrypted_bytes = bytearray()
        for i in range(len(text)):
            char_code = ord(text[i])
            key_code = ord(secret_key[i % len(secret_key)])
            encrypted_bytes.append(char_code ^ key_code)
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error encrypting token: {str(e)}")
        return str(e)

async def generate_random_string(length):
    """Generate a random alphanumeric string."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

async def generate_access_token():
    """Generate an encrypted access token."""
    plaintext = get_jupyterhub_secret_key()
    text = await generate_random_string(100) + '$$$' + plaintext
    return await encrypt(text)

async def decrypt(encoded_token):
    """Decrypt an encoded token."""
    try:
        secret_key = get_decrypt_secret_key()
        encrypted_bytes = base64.b64decode(encoded_token)
        result = ''
        for i in range(len(encrypted_bytes)):
            char_code = encrypted_bytes[i]
            key_code = ord(secret_key[i % len(secret_key)])
            result += chr(char_code ^ key_code)
        return result.split('$$$')[1]
    except Exception as e:
        print(f"Error decrypting token: {str(e)}")
        return str(e)

async def is_valid_user_token(encoded_token):
    """Validate user token."""
    try:
        username = await decrypt(encoded_token)
        if username == os.getenv("testsecter_admin"):
            return True
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if 'grader-' in username:
                cursor.execute("select id from instructor_courses where instructor = %s",(username,))
            else:
                cursor.execute("select id from students where rollno = %s",(username,))
            user = cursor.fetchone()
            return user is not None
    except Exception as e:
        print(f"Error validating user token: {str(e)}")
        return False

def date_range(start_date, end_date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)