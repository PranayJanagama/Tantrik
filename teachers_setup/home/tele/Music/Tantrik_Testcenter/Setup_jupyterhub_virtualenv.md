# New Jupyterhub setup with virtual environment
## Install MySQL server if not exists only in master
* open terminal or command prompt
* update apt <br>
`$ sudo apt update`
* install mysql server <br>
`$ sudo apt install mysql-server`
* start the server <br>
`$ sudo systemctl start mysql.service`
* configure mysql <br>
**Note:-** choose 1 for password validation policy.
Enter root user password <br>
`$ sudo mysql_secure_installation`
* Accessing mysql client <br>
`$ mysql -u root`
* set password to root user
`> ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '<password>';`
* Create database for as `tantrik` <br>
`> create database tantrik;`

[Mysql installation link for reference](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-20-04)

* Successfully completed mysql setup
## Seting system the hostname
`$ sudo hostnamectl set-hostname masternode.master.local` <br>
add system Ip and hostname. <br>
Ex:- 222.xx.222.xx masternode.master.local masternode <br>
`$ sudo nano /etc/hosts`

## Virtual environment
### Check and install python
* check weather python 3.10 exists in system or not by using command in terminal `python3.10 --version`. <br>
* if exists the command returns the version of python skip the installation steps of python. <br>
* if not installed, install python using below commands. <br>
```
sudo apt update
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev -y
```
### Create virtual environment
`$ sudo python3.10 -m venv /opt/jupyterhub/`

## Install Node 
```
$ sudo su
```
### Checking node version
`$ node -v`
* If node version is above 10 skip the below node installation <br>
### Installing Node js
```
NVM_DIR=/root/.nvm
apt install curl
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
source ~/.bashrc
NODE_VERSION=16.17.1
nvm install ${NODE_VERSION}
nvm use v${NODE_VERSION}
source ~/.bashrc
node -v
```

## Jupyterhub setup
### Install Required packages
```
$ sudo /opt/jupyterhub/bin/python3.10 -m pip install wheel

$ curl -sS https://bootstrap.pypa.io/get-pip.py | /opt/jupyterhub/bin/python3.10

$ sudo -H /opt/jupyterhub/bin/python3.10 -m pip install --ignore-installed html5lib PyYAML

$ sudo /opt/jupyterhub/bin/python3.10 -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

$ sudo /opt/jupyterhub/bin/python3.10 -m pip install -U scikit-learn scipy matplotlib tqdm torch-summary sentence-transformers transformers gensim

$ sudo /opt/jupyterhub/bin/python3.10 -m pip install jupyterhub-nativeauthenticator numpy pandas matplotlib

$ /opt/jupyterhub/bin/python3.10 -c "import torch as t; print(t.__version__);import pandas as pd;print(pd.__version__);import numpy as np;print(np.__version__);import matplotlib as mt;print(mt.__version__);"
```
### Nbgrader
* Install git in system. <br>
`$ sudo apt install git`

`$ sudo git clone https://github.com/jupyter/nbgrader /srv/nbgrader/nbgrader`

### Isuess
* if you got error as below while cloning nbgrader repo. <br>
`fatal: destination path '/srv/nbgrader/nbgrader' already exists and is not an empty directory.`
* try to check the code or remove the folder /srv/nbgrader and reclone the repo. <br>

### JupyterHub Installation files setup
`$ cd /srv/nbgrader/nbgrader/demos`

* update defalt password and add bin path to packages in below file. <br>
`$ sudo nano utils.sh`
* add (/opt/jupyterhub/bin/) before jupyter and nbgrader. <br>
* Replace the make_user funtion<br>
From
```
make_user () {
    local user="${1}"
    echo "Creating user '${user}'"
    useradd "${user}"
    yes "${user}503" | passwd "${user}"
    mkdir "/home/${user}"
    chown "${user}:${user}" "/home/${user}"
}
```
To 
```
make_user () {
    local user="${1}"
    if id -u "${user}" > /dev/null 2>&1; then
        echo "User '${user}' already exists."
    else
        echo "Creating user '${user}'"
        useradd "${user}"
        yes "${user}503" | passwd "${user}"
        mkdir "/home/${user}"
        chown "${user}:${user}" "/home/${user}"
        chmod -R g+w  "/home/${user}"
    fi
}
```

* Exit and save the file. <br>
* commenting unwanted code and adding bin paths for packages in below file. <br>
`$ sudo nano restart_demo.sh`
* Comment the below code in install_nbgrader () method. <br>
` git pull `
* add below code in install_dependencies funtion. <br>
`/opt/jupyterhub/bin/python3.10 -m pip uninstall nbgrader`
* Comment the global labextensions based on preferences.
* add (/opt/jupyterhub/bin/) before jupyter and replace (/opt/jupyterhub/bin/python3.10 -m pip) in place of pip or pip3 <br>
* comment delete existing users code in restart_demo funtion (optional)<br>
From
```
    for user in ${possible_users[@]}; do
        remove_user "${user}"
    done
```
TO
```
    # for user in ${possible_users[@]}; do
    #     remove_user "${user}"
    # done
```
* Exit and save the file. <br>

### config authenticator for jupyterhub
* Insted of using defalt authenticator, we try to use native autenticator for jupyterhub
`$ sudo nano demo_multiple_classes/jupyterhub_config.py`
* Add below code lines after c = get_config() line. <br>
```
import os, nativeauthenticator
c.JupyterHub.authenticator_class = 'native'
c.JupyterHub.template_paths = [f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"]
c.Authenticator.admin_users = {'tele'}
c.NativeAuthenticator.open_signup = True
c.ServerApp.allow_origin = '*'
```
* Replace the existing admin_users name with actual user name. You can find admin user name by refering next point. <br>
* Ex:- when u open the terminal, you will able to view the user name as (tele@DESKTOP-C8GDCP3:~$). here tele is the admin. <br>
* Exit and save the file. <br>

### Install jupyterhub setup
* Activate virtual environment. <br>
```
$ sudo su
$ source /opt/jupyterhub/bin/activate
$ cd /srv/nbgrader/nbgrader/demos
```
* By running below command we are Installing and setting jupyterhub with defult courses. <br>
`$ ./restart_demo.sh demo_multiple_classes`

* your jupyterhub installation is successfull. try to access jupyterhub from browser at `http://localhost:8000`
* stop the jupyterhub server by clicking `CTRL + c` , deactivate environment.
`$ deactivate`

### Issues
1. uninstall nbgrader 
```
Installing collected packages: nbgrader
  Attempting uninstall: nbgrader
    Found existing installation: nbgrader 0.9.4
    Uninstalling nbgrader-0.9.4:
      Successfully uninstalled nbgrader-0.9.4
  Rolling back uninstall of nbgrader
  Moving to /opt/jupyterhub/bin/nbgrader
   from /tmp/pip-uninstall-yk2v4c88/nbgrader
  Moving to /opt/jupyterhub/etc/jupyter/jupyter_server_config.d/nbgrader.json
   from /tmp/pip-uninstall-z24yczcm/nbgrader.json
  Moving to /opt/jupyterhub/lib/python3.10/site-packages/_nbgrader.pth
   from /tmp/pip-uninstall-7ud62r_m/_nbgrader.pth
  Moving to /opt/jupyterhub/lib/python3.10/site-packages/nbgrader-0.9.4.dist-info/
   from /opt/jupyterhub/lib/python3.10/site-packages/~bgrader-0.9.4.dist-info
  Moving to /opt/jupyterhub/srv/nbgrader/nbgrader/nbgrader/labextension/
   from /opt/jupyterhub/srv/nbgrader/nbgrader/nbgrader/~abextension
ERROR: Could not install packages due to an OSError: [Errno 2] No such file or directory: '/opt/jupyterhub/share/jupyter/labextensions/@jupyter/nbgrader/build_log.json'
```
* try to uninstall nbgrader using below command in new terminal. <br> 
`$ pip uninstall nbgrader`

2. user already exists
```
+ make_user instructor1
+ local user=instructor1
+ echo 'Creating user '\''instructor1'\'''
Creating user 'instructor1'
+ useradd instructor1
useradd: user 'instructor1' already exists
```
**Note:-** the user may change or different
* try to delete user . <br>
`deluser <username>`

3. Directory exists
```
[QuickStartApp | ERROR] Directory '/home/grader-course101/course101' and it's content already exists! Rerun with --force to remove this directory first (warning: this will remove the ENTIRE directory and all files in it.) 
```
**Note:-** the directory path may change or different
* add `--force` to nbgrader commands 
`$ sudo nano utils.sh`
* Update command like as below shown 
```
    ${runas} /opt/jupyterhub/bin/nbgrader quickstart "${course}" --force
    cd "${course}"
    ${runas} /opt/jupyterhub/bin/nbgrader generate_assignment ps1 --force
    ${runas} /opt/jupyterhub/bin/nbgrader release_assignment ps1 --force
```

## Course files setup from existing backup
* Open new Terminal. <br>
* Take latest backup of TAR file, save in Downloads folder. <br>
* I am assuming that the backup file name is 06-12-2024_13-00.tar.gz and exract file using below command make sure to replace file name. <br>
`$ sudo tar xzpf 06-12-2024_13-00.tar.gz`

* the extracted folder name whould be "06-12-2024_13-00" in current working directory
```
$ cd /home/tele/Downloads/06-12-2024_13-00/
$ ls
```
* Below are the listed folders and fies inside the extracted folder. <br>
 `create_course  db_backup_06-12-2024_13-00.sql  etc  home  srv  usr  var`

* Run below command to remove null characters in create course files <br>
`$ sudo find "./create_course/" -type f -exec sed -i 's/<br\/>x00//g' {} \;`

## Create Course 
* Run below command in Backup folder directory
```
$ cd create_course
$ sudo su
```
* Example current existing files in my create_course folder  
`dl2_course.sh dl3_course.sh dl2_nbgrader_config.py dl3_nbgrader_config.py`. 

* If you are working with virtual environment or jupyterhub is created in virtual environment. <br>
* we have to make changes in packages installation paths in sh file. add (/opt/jupyterhub/bin/) before thr jupyterhub and nbgrader. <br>

* I am trying to create dl2 course. the below command will create a course by using `dl2_course.sh` file. <br>
`$ ./dl2_course.sh`
* Run all the course sh file same as above command.

### Verify Created Courses
* open terminal.
1. go to home folder check whether course folder is exists or not <br>
`$ ls /home`

2. check `nbgrader_config.py` file. <br>
`$ ls grader-dl2/.jupyter` <br>
**Note:-** If file not found continue with next step, else continue with jupyterhub config.<br> 
* create nbgrader file using below command
```
$ su grader-dl2
$ cd /home/grader-dl2/.jupyter
$ nano nbgrader_config.py
```
*  add code in file
```
c = get_config()
c.CourseDirectory.root = '/home/grader-dl2/dl2'
c.CourseDirectory.course_id = 'dl2'
```
* exit user. `exit`
**Note:-** Right now we created a course. the course name is `dl2` and course admin name is ` grader-dl2`. From nest we try to config the coure in jupyterhub_config.
### Config course service in jupyterhub
* open `jupyterhub_config.py` file. <br>
`$ sudo nano /srv/nbgrader/jupyterhub/jupyterhub_config.py`
* add course users in `c.Authenticator.allowed_users` list in file.
Ex:- Becaouse I have created `dl2` course, I will add course admin `grader-dl2` in list. <br>
* add groups of course in `c.JupyterHub.load_groups` this dict like shown below
```
c.JupyterHub.load_groups = {
  ...,
  'formgrade-dl2': [
      'grader-dl2',
  ],
  'nbgrader-dl2': [
  ],
}
```
* add new course in below array. Dont remove existing courses in array. <br>
`for course in [..., 'dl2']:`
* add service to course in jupyterhub like shown below array. Dont remove existing services in array. 
```
c.JupyterHub.services = [
  ...,
  {
        'name': 'dl2',
        'url': 'http://127.0.0.1:9980',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-dl2',
        'cwd': '/home/grader-dl2',
        'environment': {
            # specify lab as default landing page
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': <add course token>,
    },
]
```
**Note:-** add the course token and change the port in url.

### Successfully course created
`exit`

# Setup Backupd files
* From Now we try to Setup files and folders from our backup
* as we discuses above we are working with only dl2 course only, if you want to setup different course, please replace the dl2 to your course name.
* Run below commands in terminal
```
$ cd /home/tele/Downloads/06-12-2024_13-00
$ sudo su
$ rsync -avz home/grader-dl2/dl2/ /home/grader-dl2/dl2/
```

* if you want to hide testcases in feedback file, run the below command. <br>
`$ cp -f -a --preserve=mode,ownership srv/nbgrader/nbgrader/nbgrader/converters/generate_feedback.py /srv/nbgrader/nbgrader/nbgrader/converters/generate_feedback.py`


* replace jupyterhub_config and database files
```
$ cp -f -a --preserve=mode,ownership srv/nbgrader/jupyterhub/jupyterhub_config.py /srv/nbgrader/jupyterhub/jupyterhub_config.py

$ cp -f -a --preserve=mode,ownership srv/nbgrader/jupyterhub/jupyterhub.sqlite /srv/nbgrader/jupyterhub/jupyterhub.sqlite
```
**Note:-** Please add your code course admin in (c.Authenticator.allowed_users), add course groups in (c.JupyterHub.load_groups), add course in (courses array) and finally add your course service in (c.JupyterHub.services) replace the tokens by generating in hub tokens of course admin.

* Now we try to copy apihandlers directory

`$ rsync -avz usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/ /opt/jupyterhub/lib/python3.10/site-packages/jupyterhub/apihandlers/`

* this [users.py](/opt/jupyterhub/lib/python3.10/site-packages/jupyterhub/apihandlers/users.py) file may contains some variable changes like token, testcenter url or secret key, ...


* Now we try to copy exchange directory
`$ rsync -avz usr/local/share/nbgrader/exchange/ /usr/local/share/nbgrader/exchange/`

* sync the datasets from any of the client or master machine in folder
```
$ mkdir -p /srv/shareddata/datasets
$ cd /srv/shareddata/
$ chmod -R 777 datasets/
```

## files and folders permissions
### home/grader-course folder
```
$ sudo chown -R grader-dl2:grader-dl2 /home/grader-dl2/
$ sudo chmod 755 /home/grader-dl2
$ sudo chmod 775 /home/grader-dl2/dl2
$ sudo chmod 775 /home/grader-dl2/.jupyter
```
### home/grader-course/.jupyter folder
`$ sudo chmod 775 /home/grader-dl2/.jupyter/nbgrader_config.py`
### home/grader-course/course folder
```
$ sudo find "/home/grader-dl2/dl2/" -type d -exec sudo chmod 755 {} \;
$ sudo chmod 2775 /home/grader-dl2/dl2/autograded
$ sudo chmod 2775 /home/grader-dl2/dl2/feedback
$ sudo chmod 2775 /home/grader-dl2/dl2/release
$ sudo chmod 775 /home/grader-dl2/dl2/submitted
$ sudo find "/home/grader-dl2/dl2/" -type f -exec sudo chmod 644 {} \;
$ sudo chmod 664 /home/grader-dl2/dl2/nbgrader_config.py
```
### /srv folder
`$ sudo chmod -R 777 /srv/shareddata`
 
### /srv/nbgrader/jupyterhub
```
$ sudo chmod 777 /srv/nbgrader/jupyterhub/jupyterhub_config.py
$ sudo chmod 644 /srv/nbgrader/jupyterhub/jupyterhub.sqlite
```

### /usr/local/lib/python3.10/dist-packages/jupyterhub/
```
$ sudo chown root:root /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/users.py
$ sudo chown root:root /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/groups.py
$ sudo chmod 644 /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/users.py
$ sudo chmod 644 /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/groups.py

```

### /usr/local/share/nbgrader/exchange
```
$ sudo chmod 777 /usr/local/share/nbgrader/exchange
$ sudo chmod -R 755 /usr/local/share/nbgrader/exchange/
$ sudo chown grader-dl2:grader-dl2 -R /usr/local/share/nbgrader/exchange/dl2/
$ sudo chmod 711 /usr/local/share/nbgrader/exchange/dl2/feedback
$ sudo chmod 2723 /usr/local/share/nbgrader/exchange/dl2/inbound
$ sudo chmod -R 777 /usr/local/share/nbgrader/exchange/dl2/inbound/
$ sudo find "/usr/local/share/nbgrader/exchange/" -type f -exec sudo chmod 655 {} \;
$ sudo find "/usr/local/share/nbgrader/exchange/dl2/outbound/" -type f -exec sudo chmod 755 {} \;
```

## the below steps are for master with 777 permissions
* Run below command to copy rsync files
`$ rsync -avz home/kmit/Desktop/ /home/tele/Desktop/`

* Run below command to copy testcenter folder
`$ rsync -avz home/kmit/Music/Tantrik_Testcentre /home/tele/Music/`

* apache setup for tantrik landing page
```
$ sudo apt install apache2
$ sudo apt install php libapache2-mod-php
$ sudo rm -f /var/www/html/index.html
$ sudo rsync -avz  var/www/html/ /var/www/html/
```

* System services
`$ sudo ln -s /home/tele/Downloads/06-12-2024_13-00/etc/systemd/system/jupyterhub.service /etc/systemd/system/jupyterhub.service`
`$ sudo ln -s /home/tele/Downloads/06-12-2024_13-00/etc/systemd/system/rsync_single_evaluation.service /etc/systemd/system/rsync_single_evaluation.service`
`$ sudo ln -s /home/tele/Downloads/06-12-2024_13-00/etc/systemd/system/testcenter-resetgpu.service /etc/systemd/system/testcenter-resetgpu.service`
`$ sudo ln -s /home/tele/Downloads/06-12-2024_13-00/etc/systemd/system/rsync-inotify.service /etc/systemd/system/rsync-inotify.service`
`$ sudo ln -s /home/tele/Downloads/06-12-2024_13-00/etc/systemd/system/testcenter.service /etc/systemd/system/testcenter.service`
**Note:-** If the above service files is deleted. the link path also is deleted.

* Dump mysql database, replace database and file with actual names
`$ mysql –u root –p [database] < [dump-file].sql`