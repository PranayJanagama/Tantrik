import subprocess
import requests
from flask import current_app

from ..utils.helpers import get_system_user

async def check_start_stop_by_host(host, course_name, assignment_name):
    command = f"ls /usr/local/share/nbgrader/exchange/{course_name}/outbound/{assignment_name}"
    try:
        ssh_command = ['/usr/bin/ssh', '-o', 'StrictHostKeyChecking=no', f'{get_system_user()}@{host}', command]
        result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
        return {"status": True, "message": result.stdout.strip()}  # Return dictionary
    except subprocess.CalledProcessError as e:
        ssh_command = ['/usr/bin/ssh', '-o', 'StrictHostKeyChecking=no', f'{get_system_user()}@{host}', command, '| echo $?']
        try:
            result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
            return {"status": False, "message": result.stderr.strip()}  # Return dictionary
        except Exception as e:
            return {"status": False, "message": str(e)} 
    
def course_students_count(course_name,host):
    total = 0
    node = f"WN{host.split('.')[3]}"
    token = current_app.config['NODE_ADMIN_TOKENS'][f"{node}"]
    try:
        headers = {'Authorization': f'token {token}'}
        response = requests.get(f'http://{host}:8000/hub/api/users', headers=headers)
        response.raise_for_status()
        users = response.json()
        group = f"nbgrader-{course_name}"
        active_users = {}
        for user in users:
            user_name = user['name']
            user_servers = user.get('servers', {})
            user_groups = user.get('groups', [])
            if group in user_groups :
                active_users[user_name] = user_servers
        total= len(active_users)
    except Exception as e:
        total = 0
        print("Error in course wise students count",str(e))
    return total