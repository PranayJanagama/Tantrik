from flask import Flask, request, jsonify
import subprocess
from flask_cors import CORS
from dotenv import load_dotenv
import os
from nbgrader.api import Gradebook
import sqlite3
import requests 
import base64

app = Flask(__name__)
CORS(app)
load_dotenv()
machines_string = os.getenv('machines', '')
machines = machines_string.split(',') if machines_string else []

@app.route('/')
def index():
    return "Hello from reset GPU"

def decrypt(encoded_token):
    try:
        encrypted_bytes = base64.b64decode(encoded_token)
        result = ''
        for i in range(len(encrypted_bytes)):
            char_code = encrypted_bytes[i]
            key_code = ord(secret_key[i % len(secret_key)])
            result += chr(char_code ^ key_code)
        return result.split('$$$')[1]
    except Exception as e:
        print("error while decrypt token ", str(e))
        return e

def is_valid_token(encoded_token):
    try:
        token = decrypt(encoded_token)
        if token == access_token:
            return True
        return False
    except Exception as e:
        print("error while validating token ",str(e))
        return False

@app.route('/resetgpumemory')
def reset_gpu_memory():
    host = request.args.get('host')
    try:
    	# Properly escape and format the shell command
        res = reset_gpu(host)
        return jsonify({"status": True, "message": res})
    except Exception as e:
        return jsonify({"status": False, "message": str(e)})
    
@app.route('/resetallsysgpumemory')
def reset_all_gpu_memory():
    responses = []
    try:
        for host in machines:
            try:   
                res = reset_gpu(host)
                responses.append({"success":True, "message":res})
            except Exception as e:
                responses.append({"success":False, "message":str(e)})
        return jsonify({"status": True, "response": responses})
    except Exception as e:
        return jsonify({"status": False,"response":responses, "message": str(e)})

def reset_gpu(host):
    try:
        ssh_command = [
                "/usr/local/bin/ansible",
                "-i", f"{host},",
                "all",
                "-m", "shell",
                "-a", f"nvidia-smi | grep 'python' | awk '{{ print $5 }}' | xargs -r -n1 kill -9",
                "-u", "root"
            ]
        result = subprocess.run(
                ssh_command, 
                capture_output=True, 
                text=True, 
                check=True, 
                env={"LC_ALL": "en_US.UTF-8"}
            )
        return result.stdout.strip()
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8580, debug=True, threaded=True)