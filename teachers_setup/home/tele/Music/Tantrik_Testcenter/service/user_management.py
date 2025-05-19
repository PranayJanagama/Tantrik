import re
import socket
import subprocess
import aiohttp
from flask import current_app

from .db import find_student_db, insert_update_student_db

from ..utils.helpers import get_node_admin_tokens
from ..utils.db import get_db_connection
from .test_center import get_xsrf_token


async def add_student_course(course, student, host, token)-> bool :
    try:
        headers = {"Authorization": f"token {token}"}
        url = f"http://{host}:8000/hub/api/groups/nbgrader-{course}/users"
        users_data = {"users": [student]}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=users_data) as response:
                response.raise_for_status()
                if response.status == 200:
                    student_db = await find_student_db(student)
                    if not student_db.get("Error"):
                        std = student_db.get("payload")
                        await insert_update_student_db(
                            rollno=student,
                            name=std[1],
                            course=course,
                            year=std[3],
                            server=std[4],
                        )
                else:
                    return False
    except aiohttp.ClientError as e:
        print(e)
        return False
    return True


async def student_search_db(rollno):
    # Search for a student
    details = {
        "rollno": "Error",
        "name": "Error",
        "course": "Error",
        "year": "Error",
        "server": "Error",
        "hub_user": "Error",
        "hub_groups": "Error",
        "system_folder": "Error",
    }
    try:
        student = await find_student_db(rollno=rollno)
        if not student.get("Error"):
            std = student.get("payload")
            details["rollno"] = std[0]
            details["name"] = std[1]
            details["course"] = std[2]
            details["year"] = std[3]
            details["server"] = std[4]

        host_match = re.search(
            r"http://([\d\.]+):\d+", current_app.config["TESTCENTER_URL"]
        )
        if host_match:
            current_host = host_match.group(1)
            ip_parts = current_host.split(".")
            if len(ip_parts) == 4 and student[4] is not None:
                new_host = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(student[4]) if isinstance(student[4], str) else student[4]}"
                headers = {
                    "Authorization": f'token {get_node_admin_tokens("WN" + student[4])}'
                }
                url = f"http://{new_host}:8000/hub/api/users/{rollno}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            hub_user = await response.json()
                            details["hub_user"] = "Exists"
                            details["hub_groups"] = hub_user["groups"]
                        else:
                            details["hub_user"] = "Not Found"
                            details["hub_groups"] = "Not Found"
                command = f"test -d /home/{rollno} && echo 'Exists' || echo 'Not Found'"
                try:
                    ssh_command = [
                        "/usr/bin/ssh",
                        "-o",
                        "StrictHostKeyChecking=no",
                        f"{current_app.config['system_user']}@{new_host}",
                        command,
                    ]
                    result = subprocess.run(
                        ssh_command, capture_output=True, text=True, check=True
                    )
                    details["system_folder"] = result.stdout
                except Exception as e:
                    details["system_folder"] = str(e)
    except Exception as e:
        print(f"Error searching for student: {str(e)}")
        pass
    finally:
        return details
