## Setup clean up files

* create cleanup folder in shareddata using below command
```
cd /srv/shareddata
mkdir cleanup
cd cleanup
```
* Copy `playwrigth/cleanup` folder from git to `/srv/shareddata/cleanup` folder.
* Run `sudo chmod 777 /srv/shareddata/cleanup/sem_end.sh` in all client terminals. (use ansable)
* Update the `/srv/manage_assignments/single_evaluation.py` file with latest code
* Restart the service
```
sudo service tantric-reevaluation stop
sudo service tantric-reevaluation start
```