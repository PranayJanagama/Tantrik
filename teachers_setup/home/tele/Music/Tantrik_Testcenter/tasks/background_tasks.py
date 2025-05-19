from flask import current_app
import asyncio
import datetime
import json
import requests

from ..service.test_center import get_all_folders, stop_active_servers, stop_assignment
from ..utils.helpers import get_external_service_urls, get_machine, get_node_admin_tokens, get_trinetra_url
from ..utils.db import get_db_connection

def trinetra_sync_task():
    sync_date = datetime.now().strftime('%Y-%m-%d')
    formatted_sync_date = datetime.strptime(sync_date, '%Y-%m-%d').strftime('%d-%m-%y')  # Format date to dd-mm-YY
    
    print(datetime.now(),"trinetra sync started")
    with current_app.app_context():
        try:
            with get_db_connection().cursor() as cursor:
                cursor.execute("select name from course;")
                courses = cursor.fetchall()
                for course in courses:
                    if course[0] =="course101":
                        continue
                    subject = "Tantrik-SDC"
                    # "SDC" if course[0] == "dl2" else "SDC-AUDI"
                    student_grades = []
                    cursor.execute("SELECT DISTINCT(assignment) FROM scores WHERE course=%s AND (assignment NOT LIKE '%%Practice%%' AND assignment NOT LIKE '%%practice%%' AND assignment NOT LIKE '%%Demo%%' AND assignment NOT LIKE '%%demo%%' AND assignment NOT LIKE 'ps1') ) AND DATE(createdon) = CURDATE();", (course[0],))
                    assignments = cursor.fetchall()
                    if assignments != () and assignments is not None:
                        query = f"""
                        SELECT 
                        score.student, 
                        SUM(CAST(SUBSTRING_INDEX(score.score, '/', 1) AS UNSIGNED))/{len(assignments)} AS score,
                        COUNT(score.score) AS num_records 
                        FROM scores score 
                        LEFT JOIN students s ON s.rollno = score.student 
                        WHERE score.course = %s
                        AND DATE(score.createdon) = CURDATE() 
                        AND (assignment NOT LIKE '%%Practice%%' AND assignment NOT LIKE '%%practice%%' AND assignment NOT LIKE '%%Demo%%' AND assignment NOT LIKE '%%demo%%' AND assignment NOT LIKE 'ps1'))
                        GROUP BY score.student, score.course;
                        """
                        cursor.execute(query, (course[0],))
                        students = cursor.fetchall()
                        for student in students:
                            data = {
                                "htno": student[0] if "ngit" not in course[0] else student[0][1:],
                                "subject": subject,
                                "totallabs":len(assignments),
                                "labsgrade":int(student[1]),
                                "totalattemptedlabs":student[2],
                                "quizgrade":0,
                                "totalquizes":0,
                                "totalattemptedquizes":0,
                                "cdate":formatted_sync_date
                            }
                            student_grades.append(data)
                        payload = {"method":3321,"students":student_grades}
                        trinetra_url = get_trinetra_url()
                        if 'ngit' in course[0]:
                            url = f"{trinetra_url}NGIT"
                            response = requests.post(url,data=json.dumps(payload), timeout=20)
                            if response.status_code == 200:
                                if response.headers['Content-Type'] == 'application/json':
                                    res = response.json()
                                    print(f"Sync performance completed for course {course[0]} message {res}")
                                else:
                                    print(f"Unexpected response format for course {course[0]}: {response.text}")
                        elif 'kmec' in course[0]:
                            url = f"{trinetra_url}KMEC"
                            response = requests.post(url,data=json.dumps(payload), timeout=20)
                            if response.status_code == 200:
                                if response.headers['Content-Type'] == 'application/json':
                                    res = response.json()
                                    print(f"Sync performance completed for course {course[0]} message {res}")
                                else:
                                    print(f"Unexpected response format for course {course[0]}: {response.text}")
                        else:
                            url = f"{trinetra_url}KMIT"
                            response = requests.post(url,data=json.dumps(payload), timeout=20)
                            if response.status_code == 200:
                                if response.headers['Content-Type'] == 'application/json':
                                    res = response.json()
                                    print(f"Sync performance completed for course {course[0]} message {res}")
                                else:
                                    print(f"Unexpected response format for course {course[0]}: {response.text}")
        except Exception as e:
            print(str(e))

def run_async_job():
    print("run_async_job started")
    asyncio.run(delete_user_sessions_cron())
    asyncio.run(stop_assignments_cron())

async def delete_user_sessions_cron():
    try:
        print("delete_user_sessions_cron started")
        with get_db_connection().cursor() as cursor:
            cursor.execute("SELECT name FROM course;")
            courses = cursor.fetchall()
            for course in courses:
                for host in get_machine():
                    node = f"WN{host.split('.')[3]}"
                    token = get_node_admin_tokens(node)
                    await stop_active_servers(host,course[0],token)
                print("delete_user_sessions_cron end", course[0] )
    except Exception as e:
        print("Error in delete_user_sessions_cron", str(e))


async def stop_assignments_cron():
    try:
        with get_db_connection().cursor() as cursor:
            cursor.execute("SELECT name FROM course;")
            courses = cursor.fetchall()
        for course in courses:
            try:
                assignments = await get_all_folders(course[0])
                for assignment in assignments:
                    if assignment[0] == 'demo' or ('Practice' in assignment) or ('practice' in assignment):
                        continue
                    try:
                        tasks = [
                            stop_assignment(course[0], assignment, external_service_url)
                            for external_service_url in get_external_service_urls(course[0])
                        ]
                        responses = await asyncio.gather(*tasks)
                    except Exception as e:
                        print(f"Error processing stoping assignment {assignment} of course {course[0]} error: {str(e)}")
            except Exception as e:
                print(f"Error processing course {course[0]} error: {str(e)}")
    except Exception as e:
        print(f"stop_assignments_cron job error: {str(e)}")