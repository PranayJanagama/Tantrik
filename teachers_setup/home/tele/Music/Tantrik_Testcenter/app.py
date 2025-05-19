import json
from flask import Flask
from flask_cors import CORS
from flask_mysqldb import MySQL  # Add this import
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os

# Import routes
from .routes.student_records import init_student_report_routes
from .routes.dataset import init_dataset_page_routes
from .routes.test_center import init_test_center_routes
from .routes.health_check import init_health_check_routes
from .routes.user_management import init_user_management_routes

# Import tasks
from .tasks.background_tasks import run_async_job, trinetra_sync_task

# Import database initialization
from .utils.db import create_tables, init_app

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app._static_folder = os.getenv("STATIC_FOLDER")
    app.config["MYSQL_HOST"] = os.getenv("DB_HOST")
    app.config["MYSQL_PORT"] = int(os.getenv("DB_PORT"))
    app.config["MYSQL_USER"] = os.getenv("DB_USER")
    app.config["MYSQL_PASSWORD"] = os.getenv("DB_PASS")
    app.config["MYSQL_DB"] = os.getenv("DATABASE")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    uploadfolder = os.path.abspath(os.getenv('UPLOAD_FOLDER'))
    os.makedirs(uploadfolder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = uploadfolder
    
    app.config['MAX_CONTENT_LENGTH'] =  5 * 1024 * 1024
    
    app.config['JUPYTERHUB_SECRET_KEY'] =os.getenv("JUPYTERHUB_SECRET_KEY")
    app.config['DECRYPT_SECRET_KEY'] = os.getenv("DECRYPT_SECRET_KEY")
    app.config['DATASETS_FOLDER'] = os.getenv("DATASETS_FOLDER")
    app.config['testsecter_admin'] =os.getenv("testsecter_admin")
    app.config['system_user'] = os.getenv("system_user")
    app.config['testsecter_admin'] = os.getenv("testsecter_admin")
    app.config['TIMEOUT_SECONDS'] = int(os.getenv("TIMEOUT_SECONDS"))

    external_service_urls_str = os.getenv("EXTERNAL_SERVICE","")  # Default to empty JSON object if not set
    try:
        # Parse the JSON string
        EXTERNAL_SERVICE_URLS = json.loads(external_service_urls_str)
    except json.JSONDecodeError:
        # Handle JSON parsing errors
        EXTERNAL_SERVICE_URLS = {}
        print("Error: The EXTERNAL_SERVICE_URLS environment variable does not contain valid JSON.")
    
    machines_string = os.getenv('machines', '')
    machines = machines_string.split(',') if machines_string else []
    
    publish_machines_string = os.getenv('publish_machines', '')
    publish_machines = publish_machines_string.split(',') if publish_machines_string else []

    NODE_ADMIN_TOKENS_STR = os.getenv("ADMIN_TOKENS","")
    try:
        # Parse the JSON string
        NODE_ADMIN_TOKENS = json.loads(NODE_ADMIN_TOKENS_STR)
    except json.JSONDecodeError:
        # Handle JSON parsing errors
        NODE_ADMIN_TOKENS = {}
        print("Error: The NODE_ADMIN_TOKENS environment variable does not contain valid JSON.")
    
    app.config['EXTERNAL_SERVICE_URLS'] = EXTERNAL_SERVICE_URLS
    app.config['machines'] = machines
    app.config['SYNC_SKIP_ASSIGNMENTS'] = os.getenv('SYNC_SKIP_ASSIGNMENTS').split(',') if os.getenv('SYNC_SKIP_ASSIGNMENTS', '') else []
    app.config['SYNC_SKIP_COURSES'] = os.getenv('SYNC_SKIP_ASSIGNMENTS').split(',') if os.getenv('SYNC_SKIP_COURSES', '') else []
    app.config['NODE_ADMIN_TOKENS'] = NODE_ADMIN_TOKENS
    app.config["ALLOWED_EXTENSIONS"] = {'csv','zip', 'rar'}
    app.config["NBGRADER_ENVIRONMENT"] = os.getenv("NBGRADER_ENVIRONMENT")
    app.config["TRINETRA_URL"] = os.getenv("TRINETRA_URL")
    app.config["publish_machines"] = publish_machines
    app.config['TESTCENTER_URL'] = os.getenv("TESTCENTER_URL")
    app.config['CLUSTER_MONITOR_PATH'] = os.getenv("CLUSTER_MONITOR_PATH")
    app.config['DATASET_PATH'] = os.getenv("DATASET_PATH")

    CORS(app, resources={r"/*": {"origins": "*"}})
    init_app(app)
    
    with app.test_request_context():
        create_tables()

    # Initialize routes
    init_test_center_routes(app)
    init_health_check_routes(app)
    init_user_management_routes(app)
    init_student_report_routes(app)
    init_dataset_page_routes(app)
    
    def run_async_job_with_context():
        with app.app_context():
            run_async_job()

    # Background scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_async_job_with_context, trigger=CronTrigger(hour=13, minute=8, second=40 ,day_of_week='mon-sat'))
    
    if os.getenv("cron") == "true":
        scheduler.add_job(trinetra_sync_task, trigger=CronTrigger(hour=19, minute=15, day_of_week='mon-sat'))

    scheduler.start()
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8581, debug=True, threaded=True)