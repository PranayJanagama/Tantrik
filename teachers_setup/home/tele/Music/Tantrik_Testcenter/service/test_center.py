import asyncio
import json
import os
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import aiohttp
from flask import current_app
from pathlib import Path

from ..utils.helpers import generate_access_token, get_dataset_folder, get_testsecter_admin, get_trinetra_url
from ..utils.db import get_db_connection

def trinetra_sync_task_on_date(sync_date=None):
    sync_date = sync_date or datetime.now().strftime('%Y-%m-%d')  # Use the provided date or default to today's date
    formatted_sync_date = datetime.strptime(sync_date, '%Y-%m-%d').strftime('%d-%m-%y')  # Format date to dd-mm-YY

    print(f"{datetime.now()} sync started for date: {sync_date}")
    
    with current_app.app_context():
        try:
            responses = []
            with get_db_connection().cursor() as cursor:
                cursor.execute("SELECT name FROM course;")
                courses = cursor.fetchall()
                
                for course in courses:
                    if course[0] == "course101":
                        continue
                    
                    subject = "Tantrik-SDC"
                    student_grades = []
                    query = f"""
                    SELECT DISTINCT(assignment) 
                    FROM scores 
                    WHERE course = %s 
                    AND (assignment NOT LIKE '%%Practice%%' AND assignment NOT LIKE '%%practice%%' AND assignment NOT LIKE '%%Demo%%' AND assignment NOT LIKE '%%demo%%' AND assignment NOT LIKE 'ps1')
                    AND DATE(createdon) = %s;
                    """
                    cursor.execute(query, (course[0], sync_date,))
                    assignments = cursor.fetchall()
                    if assignments and assignments != ():
                        query = f"""
                        SELECT 
                        score.student, 
                        SUM(CAST(SUBSTRING_INDEX(score.score, '/', 1) AS UNSIGNED))/{len(assignments)} AS score,
                        COUNT(score.score) AS num_records 
                        FROM scores score 
                        LEFT JOIN students s ON s.rollno = score.student 
                        WHERE score.course = %s
                        AND (assignment NOT LIKE '%%Practice%%' AND assignment NOT LIKE '%%practice%%' AND assignment NOT LIKE '%%Demo%%' AND assignment NOT LIKE '%%demo%%' AND assignment NOT LIKE 'ps1')
                        AND DATE(score.createdon) = %s
                        GROUP BY score.student, score.course;
                        """
                        cursor.execute(query, (course[0], sync_date))
                        students = cursor.fetchall()
                        for student in students:
                            data = {
                                "htno": student[0] if "ngit" not in course[0] else student[0][1:],
                                "subject": subject,
                                "totallabs": len(assignments),
                                "labsgrade": int(student[1]),
                                "totalattemptedlabs": student[2],
                                "quizgrade": 0,
                                "totalquizes": 0,
                                "totalattemptedquizes": 0,
                                "cdate":formatted_sync_date
                            }
                            student_grades.append(data)
                        
                        payload = {"method": 3321, "students": student_grades}
                        trinetra_url = get_trinetra_url()
                        if 'ngit' in course[0]:
                            url = f"{trinetra_url}NGIT"
                            response = requests.post(url,data=json.dumps(payload), timeout=20)
                            if response.status_code == 200:
                                if response.headers['Content-Type'] == 'application/json':
                                    res = response.json()
                                    responses.append({"status": "success", "date": f"{sync_date}","message":f"NGIT Sync performance completed for course {course[0]} message {res}"})
                                else:
                                    responses.append({"status": "success", "date": f"{sync_date}","message":f"NGIT Sync performance completed and Unexpected response format for course {course[0]}: {response.text} {url}"})                    
                        elif 'kmec' in course[0]:
                            url = f"{trinetra_url}KMEC"
                            response = requests.post(url,data=json.dumps(payload), timeout=20)
                            if response.status_code == 200:
                                if response.headers['Content-Type'] == 'application/json':
                                    res = response.json()
                                    responses.append({"status": "success", "date": f"{sync_date}","message":f"KMEC Sync performance completed for course {course[0]} message {res}"})
                                else:
                                    responses.append({"status": "success", "date": f"{sync_date}","message":f"KMEC Sync performance completed and Unexpected response format for course {course[0]}: {response.text} {url}"})                    
                        else:
                            url = f"{trinetra_url}KMIT"
                            response = requests.post(url,data=json.dumps(payload), timeout=20)
                            if response.status_code == 200:
                                if response.headers['Content-Type'] == 'application/json':
                                    res = response.json()
                                    responses.append({"status": "success", "date": f"{sync_date}","message":f"KMIT Sync performance completed for course {course[0]} message {res}"})
                                else:
                                    responses.append({"status": "success", "date": f"{sync_date}","message":f"KMIT Sync performance completed and Unexpected response format for course {course[0]}: {response.text} {url}"})                    
                    else:
                        responses.append({"status": "success", "date": f"{sync_date}","message":f"No assignments on this date course {course[0]}"})
            return responses
        except Exception as e:
            print(str(e))
            return str(e)

def date_range(start_date, end_date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)
    
async def get_unique_courses(user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if user == get_testsecter_admin():
            cursor.execute("SELECT name FROM course;")
        else:
            cursor.execute("select course from instructor_courses where instructor = %s",(user,))
        courses = cursor.fetchall()
        cursor.close()
        unique_courses = [course[0] for course in courses]
        
        def remove_items_if_exist(lst, items_to_remove):
            return [i for i in lst if i not in items_to_remove]
        
        remove_list = ["*", "default_course"]
        correct_courses = remove_items_if_exist(unique_courses, remove_list)
        return correct_courses
    except Exception as e:
        print(f"error in get courses {str(e)}")
        return []
    
async def stop_assignment(course_name, assignment_name, service_url):
    try:
        data = {'course_name': course_name, 'assignment_name': assignment_name, 'access_token':await generate_access_token()}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{service_url}unreleaseassignment", data=data) as response:
                if response.status == 200:
                    return {'url': f"{service_url}unreleaseassignment", 'status': 'Success', 'message': 'Assignment unreleased successfully.'}
                else:
                    return {'url': f"{service_url}unreleaseassignment", 'status': 'Failed', 'message': 'Assignment unreleased Failed', 'error': await response.text()}
    except Exception as e:
        return {'url': service_url, 'status': 'Failed', 'error': str(e)}
    
async def post_url(url, data):
    """Send an asynchronous HTTP POST request."""
    try:
        async with aiohttp.ClientSession() as session:
            print("Send an asynchronous HTTP POST request", "url ",url,"data ", data)
            async with session.post(url, data=data) as response:
                print(f"post_url Response from {url}: {response.status} {await response.text()}")
                return {
                    'url': url,
                    'status': 'Success' if response.status == 200 else 'Failed',
                    'message': await response.text()
                }
    except asyncio.TimeoutError:
        return {'url': url, 'status': 'Failed-timed out', 'error': 'Request timed out'}
    except aiohttp.ClientError as e:
        return {'url': url, 'status': 'Failed-error', 'error': str(e)}

async def list_folders_files(courses):
    def build_tree(directory):
        tree = {}
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    tree[item] = build_tree(item_path)
                else:
                    tree[item] = item_path  # Store the full path for each file
        except PermissionError as e:
            print(f"Permission error: {e}")
        return tree

    try:
        folder = get_dataset_folder()
        tree = {}
        for course in courses:
            course_path = os.path.join(folder, course)
            if os.path.exists(course_path) and os.path.isdir(course_path):
                tree[course] = build_tree(course_path)
            else:
                print(f"Course folder {course} does not exist or is not a directory.")
        return tree
    except Exception as e:
        print(f"An error occurred while creating tree for courses {courses}: {e}")
        return {}

async def course_admin_username_db(course_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT instructor FROM instructor_courses WHERE course = %s", (course_name,))
        course_admin_username = cursor.fetchone()[0]
        cursor.close()
        return course_admin_username
    except Exception as e:
        print(f"Error fetching course admin username: {e}")
        return None

async def get_all_folders(course_name,limit=20):
    course_admin =await course_admin_username_db(course_name)
    if not course_admin:
        return []
    path = f"/home/{course_admin}/{course_name}/release/"

    try:
        entries = await asyncio.to_thread(lambda: [Path(path) / entry for entry in os.listdir(path) if entry not in '.ipynb_checkpoints'])
        directories = sorted(
            [entry for entry in entries if entry.is_dir()],
            key=lambda x: x.stat().st_ctime,
            reverse=True
        )

        top_directories = [dir.name for dir in directories[:]]
        return top_directories
    except Exception as e:
        print("error in get_all_folders", str(e))
        return []

async def get_xsrf_token(host):
    """Fetch the _xsrf token from JupyterHub's login page."""
    try:
        url = f"http://{host}:8000/hub/login"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                xsrf_token = soup.find('input', {'name': '_xsrf'})
                
                if xsrf_token:
                    return {'success': True, 'xsrf_token': xsrf_token['value']}
                else:
                    return {'success': False, 'error': "Failed to retrieve _xsrf token from login page"}
    except aiohttp.ClientError as e:
        return {'success': False, 'error': str(e)}

async def get_active_students(host, course_name, token):
    """Fetch active students with running servers in a specific course."""
    try:
        headers = {'Authorization': f'token {token}'}
        url = f'http://{host}:8000/hub/api/users'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                users = await response.json()

                group = f"nbgrader-{course_name}"
                active_users = {}

                for user in users:
                    user_name = user.get('name')
                    user_servers = user.get('servers', {})
                    user_groups = user.get('groups', [])
                    
                    if group in user_groups and any(server.get('ready', False) for server in user_servers.values()):
                        active_users[user_name] = user_servers
                
                return active_users
    except aiohttp.ClientError as e:
        print(f"Error fetching users: {e}")
        return {}

async def stop_active_servers(host, course_name, token):
    """Stop active servers for all students in a specific course."""
    responses = []
    
    xsrf_response = await get_xsrf_token(host)
    if not xsrf_response['success']:
        error_msg = f"Error getting _xsrf token: {xsrf_response['error']}"
        return {'message': error_msg}
    
    xsrf_token = xsrf_response['xsrf_token']
    headers = {
        'Authorization': f'token {token}',
        'X-XSRFToken': xsrf_token
    }
    
    active_users = await get_active_students(host, course_name, token)
    cookies = {'_xsrf': xsrf_token}

    async with aiohttp.ClientSession() as session:
        async def stop_user_server(user_name):
            try:
                async with session.delete(
                    f"http://{host}:8000/hub/api/users/{user_name}/server",
                    headers=headers,
                    cookies=cookies
                ) as response:
                    if response.status == 204:
                        return {'user': user_name, 'success': True}
                    else:
                        error_text = await response.text()
                        return {'user': user_name, 'success': False, 'error': error_text}
            except aiohttp.ClientError as e:
                return {'user': user_name, 'success': False, 'error': str(e)}

        # Run all requests in parallel
        tasks = [stop_user_server(user) for user in active_users.keys()]
        results = await asyncio.gather(*tasks)  
    for result in results:
        if result['success']:
            responses.append({'success': True, 'message': f"Stopped server for {result['user']}."})
        else:
            responses.append({'success': False, 'error': f"Failed to stop {result['user']}: {result['error']}"})
    return responses
