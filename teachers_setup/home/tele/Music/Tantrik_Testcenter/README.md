### Freeze requirements
pip freeze > requirements.txt
### Install requirements
```pip install -r requirements.txt
   pip install "flask[async]"
```
### configure env

```
SECRET_KEY = ''

# DB
DB_HOST = ''
DB_PORT = 3306
DB_USER = ''
DB_PASS = ''
DATABASE = ''

TOKEN = '' # admin token

UPLOAD_FOLDER = 'TestCentre/uploads'

secret_key = ""
access_token = '435'

testsecter_admin = ''
DATASETS_FOLDER = '/datasets'

STATIC_FOLDER = 'TestCentre/templates/static'
system_user =  ""

machines = "localhost,127.0.0.1"

Testcenter_URL = 'http://10.11.51.225:8581/'

EXTERNAL_SERVICE_URLS = '{ course101:["http://localhost:8000"]}
'

trinetra_url = 'http://teleuniv.in/api/dronaapi.php?college='

cron = "false"
NODE_ADMIN_TOKENS = '{"WN201": "a421w3ew23zxc092"}' 
```

### Run flask application
```flask run --host=0.0.0.0 --port=8581 --debug```

# Setup backup cron job of master
```sudo crontab -e```

* add below line in file. <br>
```0 9,13,17,21 * * * /home/kmit/Music/tantrik_dev/daily_backup.sh```


### kill port process
```
sudo lsof -i :<port>
sudo kill -9 <PId>
```

# KMIT cluster services
## System service names in master
testcenter     testcenter-resetgpu   jupyterhub
rsync_apihandlers_folder     rsync-inotify  rsync_single_evaluation

## System service names in agents
tantric-reevaluation  tantrik-dl2-ngit      tantrik-dl3-ngit      jupyterhub
tantrik-course101     tantrik-dl2-nps-ngit  tantrik-dl2           tantrik-dl3    



pip install flask --ignore-installed
python3 -m pip install file.tar.gz
<!-- make sure the below packages are instal for mysqlclient-->
sudo apt-get install build-essential libmysqlclient-dev


find . -name "__pycache__" -exec rm -r {} +

sudo -u grader-elite jupyter labextension enable --level=user @jupyter/nbgrader:create-assignment

## Ansible commands
LC_ALL=en_US.UTF-8 /usr/local/bin/ansible -i '10.11.51.201,10.11.51.202,' all -m shell -a 'ls /srv/shareddata/datasets/'

LC_ALL=en_US.UTF-8 ansible all -m shell -a 'sudo service jupyterhub restart && sudo service jupyterhub status' -u root -i ~/ansible_hosts


## to zip files and folder with preserved permissions and owner
tar --preserve-permissions -czf 04-12-2024_12-19.tar.gz 04-12-2024_12-19

## to unzip files with preserved permissions and owner
sudo tar xzpf 04-12-2024_12-19.tar.gz


## student cleanup command
LC_ALL=en_US.UTF-8 ansible all -m shell -a '/bin/bash /srv/shareddata/student_exam_clean.sh /srv/shareddata/student_exam_clean.csv ps2 /srv/shareddata/student_exam_clean.txt' -u root -i ~/ansible_hosts


### Course create
ssh kmit@10.11.51.201
cd /srv/shareddata/
sudo chmod 777 elite_course.sh
sudo chmod 777 elite_nbgrader_config.py
sudo su
./elite_course.sh
exit



cd /srv/nbgrader/jupyterhub/
sudo nano jupyterhub_config.py

    'grader-elite',


    'formgrade-elite': [
        'grader-elite',
    ],
    'nbgrader-elite': [
    ],
    
    
, 'elite'


    {
        'name': 'elite',
        'url': 'http://127.0.0.1:9990',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-elite',
        'cwd': '/home/grader-elite',
        'environment': {
            # specify lab as default landing page
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': 'ad8ca125ea094b949337815d0dc146d3',
    },


sudo service jupyterhub stop
sudo service jupyterhub start