import json
import aiohttp
from flask import render_template, request, jsonify
import asyncio
import os
from datetime import datetime, timedelta
from markupsafe import Markup
import requests
import random
import string
import subprocess

from ..service.health_check import check_start_stop_by_host
from ..service.test_center import get_active_students, get_all_folders, get_unique_courses, post_url, stop_active_servers, stop_assignment, trinetra_sync_task_on_date
from ..utils.db import get_db_connection
from ..utils.helpers import date_range, decrypt, generate_access_token, get_external_service_urls, get_machine, get_node_admin_tokens, get_testsecter_admin, is_valid_user_token, get_publish_machines

def init_test_center_routes(app):

    @app.route('/testcenter')
    async def test_center():
        return f"test center{datetime.now()}"

    @app.route('/')
    async def index():
        # return render_template('index.html',user ='grader_course101')
        user_token = request.query_string.decode("utf-8").replace("access_token=", "")
        if user_token == '':
             return jsonify({"error": "Unauthorized access"}), 500
        exists = await is_valid_user_token(user_token)
        if exists == False:
            return jsonify({"error": "Unauthorized access"}), 500
           
        return render_template('index.html', user = await decrypt(user_token),token = user_token)
    
    @app.route('/get_courses')
    async def get_courses_route():
        user = request.args.get('user')
        unique_courses = await get_unique_courses(user)
        return jsonify(courses=unique_courses)

    # New Publish assignments to all clients
    @app.route('/publish', methods=['POST'])
    async def publish():
        course_name = request.form.get('course_name')
        assignment_name = request.form.get('assignment_name')
        assignment_folder = f'/home/grader-{course_name}/{course_name}/source/{assignment_name}/'
        responses = []
        for filename in os.listdir(assignment_folder):
            sourcepath = os.path.join(assignment_folder, filename)
            #f'/home/grader-{course_name}/{course_name}/source/{assignment_name}/{filename}'
    
            source_file = sourcepath  # Assuming the file to copy is the database file itself
            for external_service_url in get_external_service_urls(course_name):
                try:
                    if os.path.isfile(source_file) :
                        with open(source_file, 'rb') as f:
                            files = {'file': (os.path.basename(source_file), f)}
                            payload = {'course_name': course_name, 'assignment_name': assignment_name,'access_token':await generate_access_token()}
                            response = requests.post(f"{external_service_url}upload", files=files, data=payload)
                            if response.status_code == 200:
                                responses.append({'url': f"{external_service_url}upload", 'status': 'Success', 'message': 'Assignment published successfully' })
                            else:
                                responses.append({'url': f"{external_service_url}upload", 'status': 'Failed', 'message': 'Assignment published Failed' ,'error': response.text})
                
                except Exception as e:
                    responses.append({'url': f"{external_service_url}upload", 'status': 'Failed', 'error': str(e)})
        # Check if any request was successful
        if any(resp['status'] == 'Success' for resp in responses):
            return jsonify({'message': 'Assignment published and generated successfully.', 'responses': responses})
        else:
            return jsonify({'message': 'Error while publishing assignment to Agents.', 'responses': responses}), 500
    
    # New start assignment
    @app.route('/start_assignment',methods=['POST'])
    async def start_assignment():
        course_name = request.form.get('course_name')
        assignment_name = request.form.get('assignment_name')
        responses = []
        for external_service_url in app.config["EXTERNAL_SERVICE_URLS"][f"{course_name}"]:
            try:
                data = {'course_name': course_name,'assignment_name':assignment_name,'access_token':await generate_access_token()}
                response = requests.post(f"{external_service_url}releaseassignment",data=data)
    
                if response.status_code == 200:
                    responses.append({'url': f"{external_service_url}releaseassignment", 'status':'Success','message': 'Assignment released successfully.'})
                else:
                    responses.append({'url': f"{external_service_url}releaseassignment", 'status':'Failed','message': 'Assignment released Failed','error': response.text})
            except Exception as e:
                responses.append({'url': external_service_url, 'status': 'Failed', 'error': str(e)})
    
        if any(resp['status'] == 'Success' for resp in responses):
            return jsonify({'message': 'Assignment released successfully.', 'responses': responses})
        else:
            return jsonify({'message': 'Error while releasing assignments in Agents', 'responses': responses}), 500
    
    @app.route('/unreleaseassignment', methods=['POST'])
    async def unrelease_assignment():
        try:
            course_name = request.form.get('course_name')
            assignment_name = request.form.get('assignment_name')
            responses = []
            tasks = [
                stop_assignment(course_name, assignment_name, external_service_url)
                for external_service_url in app.config["EXTERNAL_SERVICE_URLS"][f"{course_name}"]
            ]
            responses = await asyncio.gather(*tasks)
        except Exception as e:
            responses.append({'url': 'unknown', 'status': 'Failed', 'error': str(e)})
    
        if any(resp['status'] == 'Success' for resp in responses):
            return jsonify({'message': 'Assignment unreleased successfully.', 'responses': responses})
        else:
            return jsonify({'message': 'Error while unreleasing assignments in Agents', 'responses': responses}), 500
    
    # New api to get list of students with scores
    @app.route('/gradedsubmissions',methods=['POST'])
    async def get_graded_submissions():
        course_name = request.form.get('course_name')
        assignment_name = request.form.get('assignment_name')
        json_objects = []
        if course_name is None or assignment_name is None:
                return jsonify({'status':False, 'message': f"Any of these value is null course name, assignment name","data":[]})
        try:
            for host in app.config["machines"]:
                payload={'course_name': course_name,'assignment_name': assignment_name, 'environment': app.config["NBGRADER_ENVIRONMENT"]}
                response = requests.post(f"http://{host}:8579/collectall", cookies={'access_token': await generate_access_token()}, data = payload)   
        except Exception as e:
            print(str(e))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT score.student, score.score, score.submited_on, score.server, s.name from scores score left join students s on s.rollno = score.student where score.course=%s and score.assignment = %s order by score.timestamp DESC", (course_name,assignment_name,))
            list_sub = cursor.fetchall()
            for entry in list_sub:
                json_object = {
                    "course": course_name,
                    "student": entry[0],
                    "StudentName": entry[0] if entry[4] == 'null' or entry[4] == None else entry[4],
                    "assignment": assignment_name,
                    "score": entry[1],
                    "timestamp": entry[2],
                    "server" : entry[3],
                }
                json_objects.append(json_object)
        except Exception as e:
            print("Error in retrive scores from database mysql error:",str(e))
        
        return jsonify(data = json_objects, teacher=f"grader-{course_name}")
    
    @app.route('/autograde_assignment', methods=['POST'])
    async def autograde_assignment():
        course_name = request.form.get('course_name')
        assignment_name = request.form.get('assignment_name')
        print("course_name1",course_name)
        print("assignment_name1",assignment_name)
        if not course_name or not assignment_name:
            return jsonify({'message': 'Missing required parameters'}), 400
        responses = []
        if course_name not in app.config["EXTERNAL_SERVICE_URLS"]:
            return jsonify({'message': 'Invalid course name'}), 400
        try:
            access_token = await generate_access_token()
            tasks = []
            for external_service_url in get_external_service_urls(course_name):
                try:
                    part = external_service_url.split('//')[1]
                    ip_and_port = part.split('/')[0]
                    ip = ip_and_port.split(':')[0]
                    server_number = ip.split('.')[3]
                    data = {
                        'course_name': course_name,
                        'assignment_name': assignment_name,
                        'access_token': access_token,
                        "server_number": server_number
                    }
                    print("xdw",data)
                    tasks.append(post_url(f"{external_service_url}autograde", data=data))
                    # response = requests.post(f"{external_service_url}releaseassignment",data=data)
                except Exception as e:
                    responses.append({'url': external_service_url, 'status': 'Failed', 'error': str(e)})
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict):
                    responses.append(result)
                else:
                    responses.append({'status': 'Failed', 'error': str(result)})
        except Exception as e:
            return jsonify({'message': 'Internal server error', 'error': str(e)}), 500
        return jsonify({'message': 'Autograder request processed', 'responses': responses}), 200
    
    @app.route('/feedbacktemplate')
    def render_feedback_template():
        return render_template('feedback.html',data = request.form.get('content'))
    
    @app.route('/sendfeedbackfile', methods=["POST","GET"])
    async def send_feedback_file():
        """Fetch and send the feedback file for a student."""
        course_name = request.args.get('course_name')
        assignment_name = request.args.get('assignment_name')
        student_id = request.args.get('student')
        user_token = request.args.get('user_token')
        if not user_token or user_token == '':
             return jsonify({"error": "Token Invalid"}), 500
        user = None
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("select timestamp, server from scores where student = %s and course = %s and assignment = %s ;",(student_id,course_name,assignment_name,))
                user = cursor.fetchone()
                if user is None:
                    return "User Not Found!"
        except Exception as e:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        filepath = f"/home/grader-{course_name}/{course_name}/feedback/{student_id}/{assignment_name}/"
    
        for external_service_url in app.config["EXTERNAL_SERVICE_URLS"][f"{course_name}"]:
            if str(user[1]) in external_service_url:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(f"{external_service_url}feedbackfile", data={'path': filepath, 'access_token': await generate_access_token()}) as response:
                            response.raise_for_status()
                            response_data = await response.json()
    
                            # Replace script tag for security reasons
                            script_tag = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/latest.js?config=TeX-AMS_CHTML-full,Safe'
                            commented_script_tag = 'javascript:void(0)'
                            commented_text = response_data['text'].replace(script_tag, commented_script_tag)
    
                            return render_template('feedback.html', data=Markup(commented_text))
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
        return jsonify({"error":" server ip is not saved "}),404
    
    @app.route('/getassignmentstatus')
    async def get_assignment_status():
        course_name = request.args.get('course_name')
        assignment_name = request.args.get('assignment_name')
        try:
            start = 0
            stop = 0
            tasks = [
                check_start_stop_by_host(host, course_name, assignment_name)
                for host in app.config["machines"]
            ]
            results = await asyncio.gather(*tasks)
        
            for res in results:
                if res["status"]:
                    start += 1
                else:
                    stop += 1
        
            status = "Started"
            if start == 0:
                status = "Stopped"
            elif start != 0 and stop != 0:
                status = "Partially started"
        
            return jsonify({ "Error":False, "status":status })
        except Exception as e:
            print(e, "get assignment status")
            return jsonify({ "Error":True, "status": "--" })
    
    @app.route('/courseassignments', methods=['GET'])
    async def get_all_folders_route():
        course_name = request.args.get('course_name')
        if course_name is not None or course_name != 'select-course':
            try:
                all_folders =await get_all_folders(course_name)
                return jsonify(all_folders=all_folders)
            except ValueError as e:
                return jsonify(error=str(e))
        else:
            return jsonify(error='Invalid course name')
    
    @app.route('/totalsubmittedcount')
    async def total_submitted_count():
        """Fetch total number of submitted assignments asynchronously with timeout handling."""
        course_name = request.args.get('course_name')
        assignment_name = request.args.get('assignment_name')
    
        total = 0
        responses = []
    
        async def fetch_submission_count(url):
            """Send an async request to get submission count with a timeout."""
            try:
                data = {'course_name': course_name, 'assignment_name': assignment_name, 'access_token': await generate_access_token()}
                print("totalsubmittedcount_data",data)
                response = requests.post(f"{url}submittedcount", params=data)
                if response.status == 200:
                    result = await response.json()
                    return result.get("count", 0)
                else:
                    responses.append({"service": "jupyterhub submitted_count method", "message": await response.text()})
                    return 0
            except asyncio.TimeoutError:
                responses.append({"service": "jupyterhub submitted_count method", "message": "Request timed out"})
                return 0
            except aiohttp.ClientError as e:
                responses.append({"service": "jupyterhub submitted_count method", "message": str(e)})
                return 0
    
        # Run all submission count requests concurrently with timeout
        tasks = [fetch_submission_count(url) for url in get_external_service_urls(course_name)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
        total = sum(result for result in results if isinstance(result, int))
        return jsonify({"total": total})
    
    @app.route('/totalstudentscount')
    async def total_students_count():
        """Fetch total number of students asynchronously with timeout handling."""
        course_name = request.args.get('course_name')
        total = 0
    
        async def fetch_students_count(host):
            """Send an async request to get students count with a timeout."""
            node = f"WN{host.split('.')[3]}"
            token = get_node_admin_tokens(node)
    
            try:
                headers = {'Authorization': f'token {token}'}
                search_group = f"nbgrader-{course_name}"
                timeout = aiohttp.ClientTimeout(total=app.config["TIMEOUT_SECONDS"])
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f'http://{host}:8005/hub/api/groups/{search_group}', headers=headers) as response:
                        response.raise_for_status()
                        group = await response.json()
                        if search_group in group.get('roles', []):
                            return sum(1 for user in group.get('users',[]) if not user.startswith('tp'))
            except asyncio.TimeoutError as e:
                print(e)
                return 0
            except aiohttp.ClientError as e:
                print(e)
                return 0
    
        # Run all student count requests concurrently with timeout
        tasks = [fetch_students_count(host) for host in get_machine()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
        total = sum(result for result in results if isinstance(result, int))
        return jsonify({"total": total})
    
    @app.route('/deleteusersessions', methods=['GET','DELETE'])
    async def delete_user_sessions():
        """Delete all active user sessions for a course."""
        course_name = request.args.get('course_name')
        responses = []
        tasks = [stop_active_servers(host, course_name, get_node_admin_tokens(f"WN{host.split('.')[3]}")) for host in get_machine()]
        results = await asyncio.gather(*tasks)
        for res in results:
            responses.extend(res) 
        if len(responses) == 0:
            return jsonify({'message': 'active users not found for requested course','responses': responses}),200
        elif any(resp['success'] == True for resp in responses):
            return jsonify({'message': 'Stoped all active user servers successfully.','responses': responses}),200
        else:
            return jsonify({'message': 'Failed to stoped all active user servers','responses': responses}), 500
    
    @app.route('/activestudentscount')
    async def active_students_count():
        """Get active student count."""
        course_name = request.args.get('course_name')
        total = 0
        # print([(f"WN{host.split('.')[3]}") for host in get_machine()])
        tasks = [get_active_students(host, course_name, get_node_admin_tokens(f"WN{host.split('.')[3]}")) for host in get_machine()]
        results = await asyncio.gather(*tasks)
    
        for result in results:
            total += len(result)
    
        return jsonify({"total": total})

    # New method to sync score to mysql from all clients
    @app.route('/syncscore',methods=["POST"])
    async def syncscore():
        try:
            course_name = request.form.get('course')
            assignment_name = request.form.get('assignment_name')
            student_id = request.form.get('student')
            timestamp = request.form.get('timestamp')
            submit_id = request.form.get('submit_id')
            score = request.form.get('score')
            server = request.form.get('server')
            print(f"Syncing score for {student_id} in {course_name} for {assignment_name} with score {score}")
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
            SELECT id FROM scores 
            WHERE student = %s AND assignment = %s AND course = %s
            """
            cursor.execute(query, (student_id, assignment_name, course_name,))
            existing_submission = cursor.fetchone()
            time_stamp_dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
            time_stamp_dt_adjusted = time_stamp_dt + timedelta(hours=5, minutes=30)
            if existing_submission is not None:
                # Update the existing submission
                update_query = """
                UPDATE scores 
                SET timestamp = %s, score = %s, submited_on = %s, server = %s
                WHERE id = %s
                """
                cursor.execute(update_query, (timestamp, score, time_stamp_dt_adjusted, server, existing_submission[0],))
            else:
                # Insert a new submission
                insert_query = """
                INSERT INTO scores (student, assignment, StudentName, course, timestamp, score, submited_on, server)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (student_id, assignment_name, student_id, course_name, timestamp, score, time_stamp_dt_adjusted, server,))
    
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Failed to insert or update submission in to mysqldb of user {student_id} with error {str(e)}")
        return "sync completed"

    # API route to sync between two dates
    @app.route('/sync_between_dates', methods=['GET'])
    def sync_between_dates():
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            if end_date < start_date:
                return jsonify({"error": "end_date must be greater than or equal to start_date"}), 400
            sync_results = []
            for date in date_range(start_date, end_date):
                sync_result = trinetra_sync_task_on_date(app, date.strftime('%Y-%m-%d'))
                sync_results.append(sync_result)
            return jsonify({"sync_results": json.dumps(sync_results)})
    
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    
    @app.route('/studentsreport')
    async def students_report():
        """Fetch student report for a given course and assignment."""
        course_name = request.args.get('course_name')
        assignment_name = request.args.get('assignment_name')
        try:
            data = []
            with get_db_connection().cursor() as cursor:
                cursor.execute("SELECT s.student, std.name, s.score, s.submited_on FROM students std RIGHT JOIN scores s ON std.rollno = s.student WHERE s.assignment = %s AND s.course =%s;", (assignment_name, course_name))
                students = cursor.fetchall()
                for student in students:
                    data.append({
                        "htno":student[0],
                        "name":student[0] if student[1] is None else student[1],
                        "score":student[2],
                        "submittedon":datetime.strptime(student[3], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M')
                    })
            return jsonify({"payload": data,"message":"data retrived successfully"})
        except Exception as e:
            return jsonify({"payload": [],"message":"data retrived unsuccessfully","error":str(e)})
    
    @app.route('/student_course_performance')
    def student_course_performance():
        course_name = request.args.get('course_name')
        try:
            data = []
            with get_db_connection().cursor() as cursor:
                # Fetch distinct assignments for the given course
                query = """
                SELECT DISTINCT(assignment)
                FROM scores
                WHERE course = %s
                AND assignment NOT LIKE 'ps1' AND assignment NOT LIKE '%%Practice%%' AND assignment NOT LIKE '%%practice%%'
                """
                cursor.execute(query, (course_name,))
                assignments = [row[0] for row in cursor.fetchall()]
                # Fetch all scores for the given course and assignments
                cursor.execute(
                    """
                    SELECT s.student, std.name, s.assignment, SUBSTRING_INDEX(s.score, '/', 1)
                    FROM students std
                    JOIN scores s ON std.rollno = s.student
                    WHERE s.course = %s AND assignment NOT LIKE 'ps1' AND assignment NOT LIKE '%%Practice%%' AND assignment NOT LIKE '%%practice%%'
                    ORDER BY s.student ASC, s.assignment ASC;
                    """,
                    (course_name,)
                )
                students = cursor.fetchall()
                
                student_data = {}
                max_total = len(assignments) * 100
                
                for student in students:
                    rollno = student[0]
                    name = student[1]
                    assignment = student[2]
                    score = int(student[3])
                    
                    if rollno not in student_data:
                        student_data[rollno] = {
                            "htno": rollno,
                            "name": name,
                            "assignments": {a: 0 for a in assignments},
                            "total": 0
                        }
                    
                    student_data[rollno]["assignments"][assignment] = score
                    student_data[rollno]["total"] += score
    
                for rollno, details in student_data.items():
                    details["assignments"] = [
                        {"assignment_name": assignment, "score": details["assignments"][assignment]}
                        for assignment in assignments
                    ]
                    details["avg"] = round(details["total"] * 100 / max_total, 2)
                    details["total"] = f"{details['total']}/{max_total}"
                
                data = list(student_data.values())
            
            return jsonify({"payload": {"assignments": assignments,"data": data}, "message": "Data retrieved successfully"})
        except Exception as e:
            return jsonify({"payload": [], "message": "Data retrieval unsuccessful", "error": str(e)})
    
    
    @app.route('/submissionseport')
    async def submission_seport():
        try:
            access_token = request.cookies.get('access_token')
            if access_token == '':
                return jsonify({"error": "Unauthorized access"}), 500
            admin = get_testsecter_admin()
            if access_token == admin:
                return render_template('submissionsreport.html', token = access_token, user = admin)
            exists =await is_valid_user_token(access_token)
            if exists == False:
                return jsonify({"error": "Unauthorized access"}), 500
            return render_template('submissionsreport.html', token = access_token, user =await decrypt(access_token))
        except Exception as e:
            return render_template('submissionsreport.html', user = "")
    
    @app.route('/courseperformance')
    async def course_performance():
        try:
            access_token = request.cookies.get('access_token')
            if access_token == '':
                return jsonify({"error": "Unauthorized access"}), 500
            
            admin = get_testsecter_admin()
            if access_token == admin:
                return render_template('courseperformance.html', token = access_token, user = admin)
            exists = await is_valid_user_token(access_token)
            if exists == False:
                return jsonify({"error": "Unauthorized access"}), 500
            return render_template('courseperformance.html', token = access_token, user =await decrypt(access_token))
        except Exception as e:
            return render_template('courseperformance.html', user = "")
        
        
    # @app.route('/create_course', methods=['POST'])
    # def create_course():
    #     data = request.get_json()
    #     course_name = data.get("course_name")

    #     if not course_name:
    #         return jsonify({"status": False, "message": "Missing course_name"}), 400

    #     base_path = f"/home/grader-{course_name}/{course_name}/source"
    #     try:
    #         os.makedirs(base_path, exist_ok=True)

    #         # Example config line to register course (you can adjust this part)
    #         config_line = f"# Auto-added for {course_name}\nCOURSES.append('{course_name}')\n"
    #         with open("/srv/nbgrader/jupyterhub/jupyterhub_config.py", "a") as f:
    #             f.write(config_line)

    #         return jsonify({
    #             "status": True,
    #             "message": f"Created folder structure and updated config for course '{course_name}'"
    #         })
    #     except Exception as e:
    #         return jsonify({"status": False, "message": str(e)}), 500
    @app.route('/create_course', methods=['POST'])
    def create_course():
        data = request.get_json()
        course_name = data.get("course_name")

        if not course_name:
            return jsonify({"status": False, "message": "Missing course_name"}), 400

        course_user = f"grader-{course_name}"
        service_user = course_user
        cwd_path = f"/home/{course_user}/{course_name}"
        config_file = "/srv/nbgrader/jupyterhub/jupyterhub_config.py"

        def generate_random_string(length=16):
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

        try:
            os.makedirs(cwd_path, exist_ok=True)

            with open(config_file, "r") as f:
                lines = f.readlines()

            # Check if course already exists
            if any(course_user in line for line in lines):
                return jsonify({"status": False, "message": f"Course '{course_name}' already exists."}), 409

            # 1. Add to allowed_users
            for i, line in enumerate(lines):
                if line.strip().startswith("c.Authenticator.allowed_users") and "[" in line:
                    start = i
                    while not lines[i].strip().endswith("]"):
                        i += 1
                    end = i
                    user_block = "".join(lines[start:end+1])
                    if f"'{course_user}'" not in user_block:
                        lines.insert(end, f"    '{course_user}',\n")
                    break

            # 2. Add to load_groups
            for i, line in enumerate(lines):
                if line.strip().startswith("c.JupyterHub.load_groups") and "{" in line:
                    start = i
                    while not lines[i].strip().startswith("}"):
                        i += 1
                    insert_index = i
                    lines.insert(insert_index,
                        f"    'formgrade-{course_name}': [\n"
                        f"        '{course_user}',\n"
                        f"    ],\n"
                        f"    'nbgrader-{course_name}': [\n"
                        f"        'student1',\n"
                        f"    ],\n"
                    )
                    break

            # 3. Add course_name to roles loop list
            for i, line in enumerate(lines):
                if "for course in [" in line.replace(" ", ""):
                    line = line.strip()
                    end_idx = line.find("]")
                    if end_idx != -1:
                        existing_courses = line[line.find("[")+1:line.find("]")]
                        course_list = [c.strip().strip("'") for c in existing_courses.split(",") if c.strip()]
                        if course_name not in course_list:
                            course_list.append(course_name)
                            updated_line = "for course in [" + ", ".join(f"'{c}'" for c in course_list) + "]:\n"
                            lines[i] = updated_line
                    break

            # 4. Add service block
            for i, line in enumerate(lines):
                if line.strip().startswith("c.JupyterHub.services = ["):
                    insert_index = i + 1
                    used_ports = []
                    for l in lines:
                        if "'url':" in l and "127.0.0.1" in l:
                            try:
                                port = int(l.split(":")[-1].strip().strip("',"))
                                used_ports.append(port)
                            except:
                                continue
                    next_port = max(used_ports + [9996]) + 1
                    random_token = generate_random_string()
                    service_str = (
                        f"    {{\n"
                        f"        'name': '{course_name}',\n"
                        f"        'url': 'http://127.0.0.1:{next_port}',\n"
                        f"        'command': [\n"
                        f"            'jupyterhub-singleuser',\n"
                        f"            '--debug',\n"
                        f"        ],\n"
                        f"        'user': 'grader-{course_name}',\n"
                        f"        'cwd': '/home/grader-{course_name}',\n"
                        f"        'environment': {{\n"
                        f"            'JUPYTERHUB_DEFAULT_URL': '/lab'\n"
                        f"        }},\n"
                        f"        'api_token': '{random_token}',\n"
                        f"    }},\n\n"
                    )
                    lines.insert(insert_index, service_str)
                    break

            # Save updated config
            with open(config_file, "w") as f:
                f.writelines(lines)

            # 5. Create .jupyter/nbgrader_config.py
            jupyter_config_dir = f"/home/{course_user}/.jupyter"
            os.makedirs(jupyter_config_dir, exist_ok=True)
            nbgrader_config_path = os.path.join(jupyter_config_dir, "nbgrader_config.py")
            with open(nbgrader_config_path, "w") as config_file_out:
                config_file_out.write("c = get_config()\n")
                config_file_out.write(f"c.CourseDirectory.root = '{cwd_path}'\n")
                config_file_out.write(f"c.CourseDirectory.course_id = '{course_name}'\n")

            # Set permissions (if needed)
            # subprocess.run(["chown", "-R", f"{course_user}:{course_user}", jupyter_config_dir], check=True)

            return jsonify({
                "status": True,
                "message": f"Course '{course_name}' setup completed.",
                # "url": f"http://127.0.0.1:{next_port}",
                # "token": random_token
            })

        except Exception as e:
            return jsonify({"status": False, "message": str(e)}), 500
            
    @app.route('/trigger_student_setup', methods=['POST'])
    def trigger_student_setup():
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

    @app.route('/singleevaluation', methods=["POST"])
    async def single_evaluation():
        """Perform single student assignment evaluation asynchronously."""
        try:
            course_name = request.form.get('course_name')
            assignment_name = request.form.get('assignment_name')
            student = request.form.get('student')
            server = request.form.get('server')
    
            if not all([course_name, assignment_name, student, server]):
                return jsonify({'status': False, 'message': "One or more required values are missing."})
    
            payload = {
                'course_name': course_name,
                'assignment_name': assignment_name,
                'student': student,
                'server': server,
                'access_token': await generate_access_token()
            }
    
            # for external_service_url in EXTERNAL_SERVICE_URLS[f"{course_name}"]:
            for external_service_url in get_external_service_urls(course_name):
                if server in external_service_url:
                    try:
                        timeout = aiohttp.ClientTimeout(total=20)  # Set timeout to 10 seconds
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(
                                f"{external_service_url}re-evaluate",
                                data=payload
                            ) as response:
            
                                if response.status in {200, 204}:
                                    return jsonify({'status': True, 'message': f"Successfully autograded for {student}."})
                                else:
                                    error_text = await response.text()
                                    return jsonify({'status': False, 'message': f"Failed to autograde {student}: {response.status} {error_text}"})
            
                    except asyncio.TimeoutError:
                        return jsonify({'status': False, 'message': f"Timeout error: The reevaluation request for {student} took too long."})
                    except aiohttp.ClientError as e:
                        return jsonify({'status': False, 'message': f"HTTP error during reevaluation: {str(e)}"})
    
        except Exception as e:
            return jsonify({'status': False, 'message': f"Failed to autograde {student}: {str(e)}"})