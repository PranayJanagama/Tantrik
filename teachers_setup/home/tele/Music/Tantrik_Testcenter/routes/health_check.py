import subprocess
from flask import jsonify, render_template, request
import requests

from ..utils.db import get_db_connection
from ..utils.helpers import decrypt, is_valid_user_token, get_clustermonitor_url, get_dataset_url


def init_health_check_routes(app):
    @app.route('/singlemachineping')
    def is_machine_pingable():
        host = request.args.get('host')
        if host not in app.config['machines']:
            return False
        try:
            output = subprocess.run(["/bin/ping", "-c", "2", host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return jsonify({"status": output.returncode == 0})
        except Exception as e:
            print(f"Error pinging {host}: {str(e)}")
            return jsonify({"status":False})
    
    @app.route('/healthcheck')
    async def healthcheck():
        try:
            access_token = request.cookies.get('access_token')
            if access_token == '':
                return jsonify({"error": "Unauthorized access"}), 500
            exists = await is_valid_user_token(access_token)
            if exists == False:
                return jsonify({"error": "Unauthorized access"}), 500
            if access_token == app.config["testsecter_admin"]:
                return render_template('healthcheck.html', machines=app.config['machines'], token = access_token, user = app.config["testsecter_admin"])
            return render_template('healthcheck.html', machines=app.config['machines'], token = access_token, user = await decrypt(access_token))
        except Exception as e:
            return render_template('healthcheck.html', machines=[], user = "")
    
    @app.route('/client')
    def client_healthcheck():
        host = request.args.get('host')
        course_name = request.args.get('course_name')
        if host is None or course_name is None:
            return jsonify({"status":False, "message": "Request host or course name is None"})
        elif host not in app.config['machines']:
            return jsonify({"status":False, "message": "Requested host not exists"})
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("select id from course where name = %s ;", (course_name,))
                course = cursor.fetchone()
                if course is None:
                    return jsonify({"status":False,"message":"Course not exists"})
        except Exception as e:
            return jsonify({"status":False,"message":str(e)})
        try:
            for external_service_url in app.config['EXTERNAL_SERVICE_URLS'][f"{course_name}"]:
                if host in external_service_url:
                        response = requests.get(external_service_url)
                        if response.status_code == 200:
                            return jsonify({"status":True,"message":"Agent is running"})
                        else:
                            return jsonify({"status":False,"message":"Agent is not running"})
        except Exception as e:
            return jsonify({"status":False,"message":str(e)})
    
    @app.route('/checkpublished')
    def check_published():
        host = request.args.get('host')
        course_name = request.args.get('course_name')
        assignment_name = request.args.get('assignment_name')
        # print("checkpublished_course_name",course_name)
        clusterMonitorUrl= get_clustermonitor_url()
        if host not in app.config['machines']:
            return jsonify({"status":False, "message": "Requested host not exists"})
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("select id from course where name = %s ;", (course_name,))
                course = cursor.fetchone()
                if course is None:
                    return jsonify({"status":False,"message":"Course not exists"})
        except Exception as e:
            return jsonify({"status":False,"message":str(e)})
        
        # command = f"ls /home/grader-{course_name}/{course_name}/source/{assignment_name}"
        command = f"ls {clusterMonitorUrl}/home/grader-{course_name}/{course_name}/source/{assignment_name}"
        try:
            ssh_command = ['ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command]
            result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
            return jsonify({"status":True,"message": result.stdout.strip()})
        except subprocess.CalledProcessError as e:
            ssh_command = ['ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command, ' | echo $?']
            try:
                result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
                return jsonify({"status":False,"message":  f"{result.stderr.strip()}"})
            except Exception as e:
                return jsonify({"status":False,"message": str(e)})
        except Exception as e:
            return jsonify({"status":False,"message":  "Error in client response"})
    
    async def check_start_stop_by_host(host, course_name, assignment_name):
        # command = f"ls /usr/local/share/nbgrader/exchange/{course_name}/outbound/{assignment_name}"
        clusterMonitorUrl= get_clustermonitor_url()
        command = f"ls {clusterMonitorUrl}/exchange/{course_name}/outbound/{assignment_name}"
        try:
            ssh_command = ['ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command]
            result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
            return {"status": True, "message": result.stdout.strip()}  # Return dictionary
        except subprocess.CalledProcessError as e:
            ssh_command = ['ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command, '| echo $?']
            try:
                result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
                return {"status": False, "message": result.stderr.strip()}  # Return dictionary
            except Exception as e:
                return {"status": False, "message": str(e)} 
    
    @app.route('/checkstartstop')
    async def check_start_stop():
        host = request.args.get('host')
        course_name = request.args.get('course_name')
        assignment_name = request.args.get('assignment_name')
        if host not in app.config['machines']:
            return jsonify({"status":False, "message": "Requested host not exists"})
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("select id from course where name = %s ;", (course_name,))
                course = cursor.fetchone()
                if course is None:
                    return jsonify({"status":False,"message":"Course not exists"})
        except Exception as e:
            return jsonify({"status":False,"message":str(e)})
        status = await check_start_stop_by_host(host, course_name, assignment_name)
        return status
    
    def course_students_count(course_name,host):
        total = 0
        node = f"WN{host.split('.')[3]}"
        token = app.config['NODE_ADMIN_TOKENS'][f"{node}"]
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
    
    @app.route('/systemusercount')
    def system_user_count():
        course_name = request.args.get('course_name')
        host = request.args.get('host') # 10.11.51.204
        if host not in app.config['machines']:
            return jsonify({"status":False, "message": "Requested host not exists"})
        clustermonitorUrl= get_clustermonitor_url()
        command = f"ls {clustermonitorUrl}/home | wc -l"
        course_sudents = course_students_count(course_name, host)
        try:
            ssh_command = ['ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command]
            result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
            return jsonify({"status":True, "count":  f"{result.stdout.strip()}", "couorsestudents":course_sudents})
        except subprocess.CalledProcessError as e:
            print(f"Error executing SSH command on {host}: {e}")
            ssh_command = ['ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command,' | echo $?']
            try:
                result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
                return jsonify({"status":False, "count":  f"{result.stderr.strip()}", "couorsestudents":course_sudents})
            except Exception as e:
                return jsonify({"status":False,"message": str(e)})
    
    @app.route('/checkdataset')
    def check_datasets():
        host = request.args.get('host')
        course_name = request.args.get('course_name')
        if host not in app.config['machines']:
            return jsonify({"status":False, "message": "Requested host not exists"})
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("select id from course where name = %s ;", (course_name,))
            course = cursor.fetchone()
            # cluster=get_clustermonitor_url()
            if course is None:
                return jsonify({"status":False,"message":"Course not exists"})
        command = f"find {get_dataset_url()}/srv/shareddata/datasets/{course_name}"
        try:
            ssh_command = ['ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command]
            result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
            return jsonify({"status":True,"message": f"{result.stdout.strip()}"})
        except subprocess.CalledProcessError as e:
            print(f"Error executing SSH command on {host}: {e}")
            return jsonify({"status":False,"message": str(e)})
    
    @app.route('/resetgpumemory')
    def reset_gpu_memory():
        host = request.args.get('host')
        if host not in app.config['machines']:
            return jsonify({"status":False, "message": "Requested host not exists"})
        try:
            response = requests.get(f"http://10.11.51.225:8580/resetgpumemory",params={"host":host})
            return jsonify({"status":True,"message": f"{response.json()}"})
        except Exception as e:
            print(f"Error executing {e}")
            return jsonify({"status":False,"message": str(e)})
    
    @app.route('/resetallgpumemory')
    def reset_all_gpu_memory():
        try:
            response = requests.get(f"http://10.11.51.225:8580/resetallsysgpumemory")
            return jsonify({"status":True,"message": f"{response.json()}"})
        except Exception as e:
            print(f"Error executing {e}")
            return jsonify({"status":False,"message": str(e)})
    
    @app.route('/getgpumemory')
    def get_gpu_memory():
        host = request.args.get('host')
        if host not in app.config['machines']:
            return jsonify({"status":False, "message": "Requested host not exists"})
        command = "nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv"
        try:
            ssh_command = ['/usr/bin/ssh', '-o', 'StrictHostKeyChecking=no', f"{app.config['system_user']}@{host}", command]
            result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
            return jsonify({"status":True,"message": f"{result.stdout.strip()}"})
        except subprocess.CalledProcessError as e:
            print(f"Error executing SSH command on {host}: {e}")
            return jsonify({"status":False,"message": str(e)})