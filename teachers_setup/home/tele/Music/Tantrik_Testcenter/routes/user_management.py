import csv
from datetime import datetime
import io
import os
from flask import jsonify, render_template, request, send_file
import requests
from werkzeug.utils import secure_filename

from ..service.user_management import add_student_course, student_search_db
from ..playwright_cleanup.add_signup_enroll.addhubusers import addhub_main
from ..playwright_cleanup.add_signup_enroll.enrollstudentstocourse import enrollcourse_main
from ..playwright_cleanup.add_signup_enroll.signup_users import signup_main
from ..utils.db import get_db_connection
from ..utils.helpers import allowed_file, get_machine, get_node_admin_tokens, get_testsecter_admin, get_upload_folder, is_valid_user_token, get_publish_machines


def init_user_management_routes(app):

    @app.route('/manageusers')
    async def manage_user():
        user_token = request.query_string.decode("utf-8").replace(
            "access_token=", "")
        if user_token == '':
            return jsonify({"error": "Unauthorized access"}), 500
        exists = await is_valid_user_token(user_token)
        if exists == False:
            return jsonify({"error": "Unauthorized access"}), 500
        return render_template('manage_users.html',
                               user=get_testsecter_admin())

    @app.route("/add_course", methods=["POST"])
    def add_course():
        try:
            course_name = request.form.get("course_name")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
            INSERT INTO course (name)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE name=VALUES(name);
            """, (course_name, ))
            conn.commit()
            cursor.close()
            return jsonify({
                "message": 'uploaded successfully',
                "redirect_url": "/manageusers"
            })
        except Exception as e:
            return jsonify({"message": str(e), "redirect_url": "/manageusers"})

    @app.route('/addinstructor', methods=["POST"])
    def add_instructor():
        try:
            course_name = request.form.get("course_name")
            instructor = request.form.get("instructor")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
            INSERT INTO instructor_courses (instructor, course, created_at, updated_at)
            VALUES (%s, %s, CURDATE(),CURDATE())
            ON DUPLICATE KEY UPDATE instructor=VALUES(instructor), course=VALUES(course), updated_at=CURDATE();
            """, (
                    instructor,
                    course_name,
                ))
            conn.commit()
            cursor.close()
            return jsonify({
                "message": 'uploaded successfully',
                "redirect_url": "/manageusers"
            })
        except Exception as e:
            return jsonify({"message": str(e), "redirect_url": "/manageusers"})

    @app.route('/bulkaddstudents', methods=["POST"])
    async def bulk_add_students():
        success_count = 0
        fail_count = 0
        detailed_results = []

        try:
            course = request.form.get("course_name")
            adminuser = request.form.get("adminuser")
            adminpassword = request.form.get("adminpassword")
            hostip = request.form.get("hostip")

            if hostip not in get_machine():
                return jsonify({"message": "Requested host does not exist"})

            server = hostip.split('.')[3]
            uploadpath = get_upload_folder()

            if 'csv_file' not in request.files:
                return jsonify({
                    "message": 'No file part',
                    "redirect_url": "/manageusers"
                })
            file = request.files['csv_file']
            if file.filename == '':
                return jsonify({
                    "message": 'No file selected for uploading',
                    "redirect_url": "/manageusers"
                })

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(uploadpath, filename)
                file.save(filepath)

                with open(filepath, mode='r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        rollno = row['username'].strip()
                        name = row['name'].strip()
                        year = int(row["year"].strip())
                        user_result = {
                            "username": rollno,
                            "name": name,
                            "steps": {
                                "folder_create": "Error",
                                "signup": "Error",
                                "add_to_hub": "Error",
                                "enroll_course": "Error",
                                "database": "Error",
                            },
                            "response": {
                                "folder_create": "",
                                "signup": "",
                                "add_to_hub": "",
                                "enroll_course": "",
                                "database": "",
                            },
                        }
                        try:
                            node = f"WN{server}"
                            token = get_node_admin_tokens(node)
                            headers = {'Authorization': f'token {token}'}
                            student = await student_search_db(name)
                            if student["system_folder"] == "Error":
                                res = requests.get(
                                    f"http://{hostip}:8579/createhomefolder",
                                    params={"rollno": rollno})
                                if res.status_code == 200:
                                    user_result["steps"][
                                        "folder_create"] = "Success"
                                elif res.status_code == 400:
                                    user_result["steps"][
                                        "folder_create"] = "Exists"
                            else:
                                user_result["steps"][
                                    "folder_create"] = "Exists"
                            print("folder_create")
                            if student["hub_user"] == "Error" or student[
                                    "hub_user"] == "Not Found":
                                res = requests.post(
                                    f"http://{hostip}:8000/hub/api/users",
                                    headers=headers,
                                    json={
                                        "name": name,
                                        "username": rollno
                                    })
                            user_result["response"][
                                "folder_create"] = res.json()["message"]
                            res = requests.get(
                                f"http://{hostip}:8000/hub/api/users/{rollno}",
                                headers=headers)
                            if res.status_code == 200:
                                user_result["steps"]["signup"] = "Exists"
                                user_result["response"][
                                    "signup"] = "User already exists"
                                user_result["response"][
                                    "add_to_hub"] = "User already exists"
                            else:
                                # above code is working fine
                                user_result["response"]["signup"] = res.json(
                                )["message"]
                                res_signup = await signup_main(rollno, hostip)
                                user_result["response"]["signup"] = user_result["response"]["signup"] + \
                                    res_signup['message']
                                if res_signup['success']:
                                    user_result["steps"]["signup"] = "Success"
                                    res_addhub = await addhub_main(
                                        adminuser, adminpassword, rollno,
                                        hostip)
                                    user_result["response"][
                                        "add_to_hub"] = res_addhub['message']
                                    if res_addhub['success']:
                                        user_result["response"][
                                            "add_to_hub"] = "Success"
                                else:
                                    continue
                            res_json = res.json()
                            print("res_json", res_json['groups'])
                            if f"nbgrader-{course}" in res_json['groups']:
                                user_result["steps"][
                                    "enroll_course"] = "Exists"
                                user_result["response"][
                                    "enroll_course"] = "User already in course group"
                            else:
                                res_enroll = await enrollcourse_main(
                                    adminuser, adminpassword, rollno, hostip,
                                    course)
                                user_result["response"][
                                    "enroll_course"] = res_enroll['message']
                                if res_enroll['success']:
                                    user_result["steps"][
                                        "enroll_course"] = "Success"
                            print(user_result)
                            conn = None
                            try:
                                conn = get_db_connection()
                                with conn.cursor() as cursor:
                                    cursor.execute(
                                        """
                                        INSERT INTO students (rollno, name, course, year, server)
                                        VALUES (%s, %s, %s, %s, %s)
                                        ON DUPLICATE KEY UPDATE name=VALUES(name), course=VALUES(course), year=VALUES(year), server=VALUES(server);
                                    """, (rollno, name, course, year, server))
                                conn.commit()
                                user_result["steps"]["database"] = "Success"
                                user_result["response"][
                                    "database"] = "Details updated in database"
                            except Exception as e:
                                user_result["response"]["database"] = str(e)
                            finally:
                                if conn:
                                    conn.close()
                            print("user_result", user_result)
                            success_count += 1
                        except Exception as e:
                            print(str(e))
                            user_result["error"] = str(e)
                            fail_count += 1
                        detailed_results.append(user_result)
            else:
                return jsonify({
                    "message":
                    "Invalid file type. Only CSV files are allowed.",
                })

        except Exception as e:
            return jsonify({
                "message":
                f"An unexpected error occurred: {str(e)}",
            })

        return jsonify({
            "message":
            f"Bulk addition completed. {success_count + fail_count} total, {success_count} successful, {fail_count} failed.",
            "summary": {
                "success_count": success_count,
                "fail_count": fail_count,
                "total": success_count + fail_count
            },
            "details": detailed_results,
        })


    @app.route('/publish_course', methods=['POST'])
    def publish_course():
        data = request.get_json()
        course_name = data.get("course_name")

        if not course_name:
            return jsonify({"status": False, "message": "course_name is required", "errors": []})

        errors = []
        for external_service_url in get_publish_machines():
            try:
                response = requests.post(
                    f"{external_service_url}:8005/hub/api/setup_student_home",
                    json=data,
                    timeout=5
                )
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {
                        "status": False,
                        "message": "Invalid JSON response",
                        "raw_response": response.text
                    }


                if response.status_code != 200 or not response_data.get("status"):
                    errors.append({external_service_url: response_data})

            except Exception as e:
                errors.append({external_service_url: str(e)})

        if errors:
            return jsonify({"status": False, "message": "Some setups failed", "errors": errors})
        return jsonify({"status": True, "message": "All student setups completed successfully"})

    @app.route('/download_sample_csv')
    def download_sample_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['username', 'name', 'year'])
        writer.writerow(['22bd1a0xx', 'John', 2])
        writer.writerow(['22bd1a0xx', 'Smith', 2])
        writer.writerow(['22bd1a0xx', 'David', 2])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name='sample_students.csv')

    @app.route('/cleanup_students', methods=["POST"])
    def cleanup_students():
        try:
            request_data = request.form.to_dict()
            if 'csv_file' not in request.files:
                return jsonify({
                    "message": 'No file part',
                    "redirect_url": "/manageusers"
                }), 415

            file = request.files['csv_file']
            if file.filename == '':
                return jsonify({
                    "message": 'No file selected for uploading',
                    "redirect_url": "/manageusers"
                })
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                folder = "/srv/shareddata/cleanup"
                if not os.path.exists(folder):
                    os.makedirs(folder)

                filepath = os.path.join(folder, filename)
                file.save(filepath)

                request_data.pop('csv_file', None)
                responses = []

                log_folder = os.path.join(os.getcwd(), "logs")
                if not os.path.exists(log_folder):
                    os.makedirs(log_folder)  # Ensure the logs folder exists

                log_file = os.path.join(
                    log_folder,
                    f"cleanup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
                )
                open(log_file, 'a').close()

                for host in get_machine():
                    data = {**request_data, "csvfilepath": filepath}
                    try:
                        response = requests.post(
                            f"http://{host}:8579/cleanup_student_data",
                            data=data)
                        res_data = response.json()
                        responses.append({
                            "host": host,
                            "response": res_data["message"]
                        })

                        with open(log_file, 'a') as file:
                            file.write("+" * 50 + "\n")
                            file.write(f"Host: {host}\n")
                            file.write(res_data["output"] + "\n")

                    except Exception as e:
                        responses.append({"host": host, "response": str(e)})

                        with open(log_file, 'a') as file:
                            file.write("+" * 50 + "\n")
                            file.write(f"Host: {host} - Exception occurred\n")
                            file.write(str(e) + "\n")

                response_data = {
                    "message": "Cleanup completed successfully",
                    "responses": responses,
                    "log_file_link":
                    f"/download_log/{os.path.basename(log_file)}"
                }
                return jsonify(response_data), 200
            else:
                return jsonify({
                    "message":
                    'Invalid file type. Only CSV files are allowed.',
                    "redirect_url": "/manageusers"
                }), 415

        except Exception as e:
            return jsonify({
                "message": str(e),
                "redirect_url": "/manageusers"
            }), 400

    @app.route('/download_log/<filename>', methods=["GET"])
    def download_log(filename):
        log_file_path = os.path.join(os.getcwd(), "logs", filename)
        if os.path.exists(log_file_path):
            return send_file(log_file_path,
                             as_attachment=True,
                             download_name=filename,
                             mimetype='text/plain')
        else:
            return jsonify({"error": "File not found"}), 404

    @app.route('/student_search', methods=["POST"])
    async def student_search():
        try:
            student = request.form.get('student')
            print("student_search", student)
            return jsonify({
                "message": "Search successful",
                "details": await student_search_db(student)
            }), 200
        except Exception as e:
            return jsonify({"message": str(e)}), 500

    @app.route('/enrollstudentstocourse', methods=["POST"])
    async def enroll_students_course():
        try:
            course = request.form.get("course_name")
            uploadpath = get_upload_folder()

            if 'csv_file' not in request.files:
                return jsonify({
                    "message": 'No file part',
                }), 400

            file = request.files['csv_file']
            if file.filename == '':
                return jsonify({
                    "message": 'No file selected for uploading',
                }), 400

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(uploadpath, filename)
                file.save(filepath)

                with open(filepath, mode='r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    success_student = []
                    for row in reader:
                        rollno = row['username'].strip()
                        host = row['host']
                        if host in get_machine():
                            res = await add_student_course(
                                course, rollno, host,
                                get_node_admin_tokens(
                                    f"WN{host.split('.')[3]}"))
                            if res:
                                success_student.append(rollno)

                return jsonify({
                    "message": f"Successfully enrolled students",
                    "payload": success_student
                }), 200
            return jsonify({
                "message": 'Invalid file type',
            }), 400

        except Exception as e:
            return jsonify({
                "message": str(e),
            }), 500
