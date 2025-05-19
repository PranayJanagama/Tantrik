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
Testcenter_URL = os.getenv("Testcenter_URL")
secret_key = os.getenv("DECRYPT_SECRET_KEY")
access_token = os.getenv("JUPYTERHUB_SECRET_KEY")

@app.route('/')
def index():
    return "Hello from single evaluation1"

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

@app.route('/reevaluate', methods=['POST'])
def reevaluate():
    print(request.form.get('server'))
    access_token = request.cookies.get('access_token')
    if not is_valid_token(access_token):
        return jsonify({'message': f'Unauthorized access token error'}), 500
    coursename = request.form.get('course_name')
    assignmentname = request.form.get('assignment_name')
    student = request.form.get('student')
    server = request.form.get('server')

    home = f"/home/grader-{coursename}"
    runas = f"sudo -u grader-{coursename}"
    currdir = os.getcwd()
    course = f"/home/grader-{coursename}/{coursename}"
    try:
        subprocess.run(
            f"find '/home/grader-{coursename}/{coursename}/submitted' -type f -exec chmod 777 {{}} \;",
            shell=True,
            check=True
        )
        subprocess.run(
            f"find '/home/grader-{coursename}/{coursename}/autograded' -type f -exec chmod 777 {{}} \;",
            shell=True,
            check=True
        )
        subprocess.run(
            f"find '/home/grader-{coursename}/{coursename}/feedback' -type f -exec chmod 777 {{}} \;",
            shell=True,
            check=True
        )
        subprocess.run(f"{runas} nbgrader collect {assignmentname} --update", shell=True, check=True)
        subprocess.run(
            f"find '/home/grader-{coursename}/{coursename}/' -type d -exec chown grader-{coursename}:grader-{coursename} {{}} \;",
            shell=True,
            check=True
        )
        subprocess.run(
            f"find '/home/grader-{coursename}/{coursename}/' -type f -exec chown grader-{coursename}:grader-{coursename} {{}} \;",
            shell=True,
            check=True
        )
        try:
            subprocess.run(f"{runas} nbgrader autograde {assignmentname} --student {student}", shell=True, check=True)
        except Exception as e:
            try:
                subprocess.run(f"{runas} nbgrader autograde {assignmentname} --student {student} --force", shell=True, check=True)
            except Exception as e:
                print(f"autograder student {student} error {str(e)}")
                raise e
                
        try:
            subprocess.run(f"chown -R grader-{coursename}:grader-{coursename} /usr/local/share/nbgrader/exchange/{coursename}/feedback/", shell=True, check=True)
            subprocess.run(f"{runas} nbgrader generate_feedback {assignmentname} --student {student}", shell=True, check=True)
        except Exception as e:
            try:
                subprocess.run(f"{runas} nbgrader generate_feedback {assignmentname} --student {student} --force", shell=True, check=True)
            except Exception as e:
                print(f"generate_feedback student {student} error {str(e)}")
                raise e
               
        try:
            subprocess.run(f"{runas} nbgrader release_feedback {assignmentname} --student {student}", shell=True, check=True)
        except Exception as e:
            print(f"release_feedback student {student} error {str(e)}")
            raise e

        db_path = os.path.join(home, coursename, 'gradebook.db')
        res = graded_students(db_path,assignmentname,student, server)
        return jsonify({'message': f'assignment autograded successfully {res}'}), 200

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the command: {e}")
        return jsonify({'message': f'Error in autograde assignment: {str(e)}'}), 500

    finally:
        os.chdir(currdir)

@app.route('/collectall', methods=['POST'])
def collectall():
    access_token = request.cookies.get('access_token')
    if not is_valid_token(access_token):
        return jsonify({'message': f'Unauthorized access token error'}), 500
    coursename = request.form.get('course_name')
    assignmentname = request.form.get('assignment_name')
    environment = request.form.get('environment')

    runas = f"sudo -u grader-{coursename}"
    currdir = os.getcwd()
    if environment == 'venv':
        command = f"{runas} /opt/jupyterhub/bin/nbgrader collect {assignmentname} --update"
    else:
        command = f"{runas} nbgrader collect {assignmentname} --update"
    try:
        subprocess.run(command, shell=True, check=True)
        return jsonify({'message': f'assignment collected successfully'}), 200
    except Exception as e:
        print("Error in collect APi",str(e))
        return jsonify({'message': f'Error in collecting assignment: {str(e)}'}), 500
    finally:
        os.chdir(currdir)

def graded_students(db_path,assignment_name,student,server):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT a.course_id,s.student_id,s.timestamp, s.id FROM submitted_assignment s join assignment a on a.id = s.assignment_id WHERE a.name = ? and s.student_id = ?;", (assignment_name,student,))
        list_sub = cursor.fetchall()
        json_objects = []
        for student in list_sub:
            json_object = {
                "course": student[0],
                "assignment_name": assignment_name,
                "student": student[1],
                "timestamp": student[2],
                "server": server,
                "submit_id": student[3],
                "score": get_grade_of_student(db_path,assignment_name,student[1])
            }
            try:
                response = requests.post(f"{Testcenter_URL}/syncscore",data=json_object)
                print(response)
                if response.status_code == 200:
                    print("grade submitted successfully",json_object["student"])
                else:
                    print("grade submit not successful",json_object["student"])
            except Exception as e:
                print("get_graded_submissions+++++++++++",str(e))
        conn.close()
        print("json_objects",json_objects)
        return json_objects
    except Exception as e:
        return e

def get_grade_of_student(db_path,assignment_name,student_id):
    if os.path.exists(db_path):
        with Gradebook(f'sqlite:///{db_path}') as gb:
            try:
                submission =  gb.find_submission(assignment_name, student_id)
                score_str = f"{int(submission.score)}/{int(submission.max_score)}" if submission.score is not None or submission.max_score !='null' else "NG"
                print("get_grade_of_student score", score_str)
                return score_str
            except Exception as e:
                print("get_grade_of_student error",str(e))
                return 'NG'

@app.route('/cleanup_student_data', methods=["POST"])
def cleanup_student_data():
    try:
        csvfilepath = request.form.get("csvfilepath")
        course = request.form.get("course_name")
        unenroll = request.form.get("unenroll")
        if not csvfilepath or not course:
            return jsonify({"error": "All parameters (csvfilepath, course) are required."}), 400
        
        output_file = os.path.join("/srv/shareddata/cleanup", "cleanup_output.txt")
        if os.path.exists(output_file):
            with open(output_file, 'w') as file:
                file.close()

        command = [
            "sudo",
            "bash",
            "/srv/shareddata/cleanup/sem_end.sh",
            csvfilepath,
            course,
            unenroll,
            output_file
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if os.path.exists(output_file):
            with open(output_file, 'r') as file:
                file_content = file.read()

        if result.returncode == 0:
            return jsonify({
                "message": "Cleanup successful",
                "output":  file_content
            }), 200
        else:
            return jsonify({"message": "Cleanup failed", "output": result.stderr}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/createhomefolder')
def create_home_folder():
    try:
        rollno = request.args.get("rollno")
        folder_path = f"/home/{rollno}"
        if not os.path.exists(folder_path):
            command = [
                "useradd", "-m", rollno,
                "&&", "chmod", "-R", "775", folder_path,
                "&&", "chown", f"{rollno}:{rollno}", folder_path
            ]
            result = subprocess.run(
                " ".join(command),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                return jsonify({
                    "Status": True,
                    "message": "User folder creation successful",
                }), 200
            else:
                return jsonify({
                    "Status": False,
                    "message": f"Error: {result.stderr}",
                }), 500
        else:
            return jsonify({
                "Status": False,
                "message": "Folder already exists",
            }), 400
    except Exception as e:
        return jsonify({
            "Status": False,
            "message": f"An error occurred: {str(e)}",
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8579, debug=True, threaded=True)
