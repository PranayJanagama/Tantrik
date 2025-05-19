#!/bin/bash

set -euo pipefail

# Directories
REMOTE_DIR='/home/kmit/Documents/tantrik-225-master-backups/regular'
CURRENT_DIR='/home/kmit/Documents/tantrik-225-master-backups/regular'
JUPYTERHUB='/srv/nbgrader/jupyterhub'
DATASETS='/srv/shareddata/datasets'
APIHANDLER='/usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers'
USERS_DIR='/home'
EXCHANGE_DIR='/usr/local/share/nbgrader/exchange'
RSYNC_DIR='/home/kmit/Desktop'
HTML_DIR='/var/www/html'
TESTCENTER='/home/kmit/Music/Tantrik_Testcentre'
SYS_SERVICE='/etc/systemd/system'
COURSE_SH_FOLDER='/home/kmit/Documents/jupyterhub-k8s/tantrik_create_course'
ANSIBLE_BIN='/usr/local/bin/ansible'
REMOTE_IP='10.11.51.212'
GENERATE_FEADBACK='/srv/nbgrader/nbgrader/nbgrader/converters'

# MySQL credentials
MYSQL_USER='root'
MYSQL_PASS='TeleAdmin321$'
MYSQL_DATABASE='tantrik'

# Generate timestamps
DB_BACKUP="db_backup_$(date +"%d-%m-%Y_%H-%M")"
NEW_DIR="$(date +"%d-%m-%Y_%H-%M")"

# Ensure the base backup directory exists
mkdir -p "$CURRENT_DIR"
cd "$CURRENT_DIR" || {
    printf "Failed to access %s\n" "$CURRENT_DIR" >&2
    exit 1
}

# Create a new backup directory
mkdir -p "$NEW_DIR"
cd "$NEW_DIR" || {
    printf "Failed to create %s\n" "$NEW_DIR" >&2
    exit 1
}

# MySQL Backup
printf "Starting MySQL backup...\n"
if ! mysqldump -u "$MYSQL_USER" -p"$MYSQL_PASS" "$MYSQL_DATABASE" >"$DB_BACKUP.sql" 2>/dev/null; then
    printf "MySQL backup failed.\n" >&2
    exit 1
fi
printf "MySQL backup completed: %s.sql\n" "$DB_BACKUP"

# Backup courses
COURSES=("course101" "dl2" "dl2-ngit" "dl3" "dl3-ngit" "dl3-nps-ngit" "dl2-nps-ngit")

backup_course() {
    local course=$1
    local course_dir="$USERS_DIR/grader-$course"
    local dest_dir="home/grader-$course"
    # local dest_dir="home/grader-$course/$course"

    if [[ -d "$course_dir" ]]; then
        printf "Processing course: %s\n" "$course"
        mkdir -p "$dest_dir"
        if ! rsync -a "$course_dir/" "$dest_dir/"; then
            printf "Failed to copy course folder for course %s\n" "$course" >&2
        fi
    else
        printf "Directory for %s not found, skipping...\n" "$course"
    fi
}

for course in "${COURSES[@]}"; do
    backup_course "$course"
done

printf "home folder backup completed\n"

# Function to copy directories or files
copy_dir_or_file() {
    local src=$1
    local dest=$2

    cd "$CURRENT_DIR"
    cd "$NEW_DIR"
    if [[ -e "$src" ]]; then
        mkdir -p --mode=0755 "$(dirname "$dest")" || {
            printf "Failed to create directory for %s.\n" "$dest" >&2
            return 1
        }
        if ! rsync -a "$src/" "$dest/"; then
            printf "Failed to copy %s to %s.\n" "$src" "$dest" >&2
        fi
        # cp -a --preserve=mode,ownership "$src" "$dest" || {
        #     printf "Failed to copy %s to %s.\n" "$src" "$dest" >&2
        # }
    else
        printf "%s not found, skipping...\n" "$src"
    fi
}


# Copy additional directories
# copy_dir_or_file "$DATASETS" "srv/shareddata/datasets"
# printf "datasets folder backup completed\n"

copy_dir_or_file "$APIHANDLER" "usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers"
printf "apihandler folder backup completed\n"

copy_dir_or_file "$JUPYTERHUB" "srv/nbgrader/jupyterhub"
printf "jupyterhub folder backup completed\n"

copy_dir_or_file "$EXCHANGE_DIR" "usr/local/share/nbgrader/exchange"
printf "exchange folder backup completed\n"

copy_dir_or_file "$RSYNC_DIR" "home/kmit/Desktop"
printf "rsync folder backup completed\n"

copy_dir_or_file "$HTML_DIR" "var/www/html"
printf "html folder backup completed\n"

copy_dir_or_file "$TESTCENTER" "home/kmit/Music/Tantrik_Testcentre"
printf "Tantrik_Testcentre folder backup completed\n"

copy_dir_or_file "$COURSE_SH_FOLDER" "create_course"
printf "COURSE_SH_FOLDER folder backup completed\n"

cd "$CURRENT_DIR/$NEW_DIR"

printf "generate_feadback.py file backup start\n"

if [[ -d "$GENERATE_FEADBACK" ]] && [[ -f "$GENERATE_FEADBACK/generate_feedback.py" ]]; then
    folder_path='srv/nbgrader/nbgrader/nbgrader/converters'
    mkdir -p "$folder_path" || {
        printf "Failed to create directory %s.\n" "$folder_path" >&2
        return 1
    }
    cp -a --preserve=mode,ownership "$GENERATE_FEADBACK/generate_feedback.py" "$folder_path" || {
        printf "Failed to copy generate_feedback.py from %s to %s.\n" "$GENERATE_FEADBACK/generate_feedback.py" "$folder_path" >&2
        return 1
    }
else
    printf "convertors folder or generate_feadback.py file %s not found, skipping...\n" "$GENERATE_FEADBACK/generate_feedback.py"
fi

# Backup system services
mkdir -p --mode=0755 "etc/systemd/system"
SERVICE_FILES=("testcenter-resetgpu" "testcenter" "rsync-inotify" "rsync_single_evaluation" "rsync_apihandlers_folder" "jupyterhub")

for service in "${SERVICE_FILES[@]}"; do
    service_path="$SYS_SERVICE/$service.service"
    if [[ -f "$service_path" ]]; then
        cp -a --preserve=mode,ownership "$service_path" "etc/systemd/system" || {
            printf "Failed to copy service file %s.\n" "$service_path" >&2
        }
    else
        printf "Service %s not found, skipping...\n" "$service_path"
    fi
done

printf "Service files backup completed\n"

# Create a zip archive
printf "Creating zip archive...\n"
cd "$CURRENT_DIR"
if ! tar --preserve-permissions -czf "$NEW_DIR.tar.gz" "$NEW_DIR"; then
    printf "Failed to create zip archive.\n" >&2
    exit 1
fi
printf "Created zip archive\n"

# Clean up
rm -rf "$NEW_DIR"

# Transfer the backup
printf "Transferring the backup to remote server...\n"
if ! scp "$NEW_DIR.tar.gz" "root@$REMOTE_IP:$REMOTE_DIR"; then
    printf "Failed to transfer backup to remote server.\n" >&2
    exit 1
fi
printf "Transferring the backup to remote server completed\n"

# Remove old ZIP and tar.gz files in 212
printf "Removing the backup tar.gz files on the remote server...\n"
if ! LC_ALL=en_US.UTF-8 "$ANSIBLE_BIN" -i "$REMOTE_IP," all -m shell -a "find '$REMOTE_DIR' -name '*.tar.gz' -type f -mtime +30 -exec rm -v {} \;" -u root; then
    printf "Failed to remove tar.gz files on the remote server at %s.\n" "$REMOTE_IP" >&2
    exit 1
fi
printf "Removing the backup tar.gz files on the remote server completed successfully.\n"

printf "Removing tar.gz files older than 30 days in current server...\n"
find "$CURRENT_DIR" -name "*.tar.gz" -type f -mtime +30 -exec rm -v {} \;
printf "Removing tar.gz files older than 30 days completed\n"


printf "Removing the backup ZIP files on the remote server...\n"
if ! LC_ALL=en_US.UTF-8 "$ANSIBLE_BIN" -i "$REMOTE_IP," all -m shell -a "find '$REMOTE_DIR' -name '*.zip' -type f -mtime +30 -exec rm -v {} \;" -u root; then
    printf "Failed to remove ZIP files on the remote server at %s.\n" "$REMOTE_IP" >&2
    exit 1
fi
printf "Removing the backup ZIP files on the remote server completed successfully.\n"

# Remove old ZIP files
printf "Removing ZIP files older than 30 days in current server...\n"
find "$CURRENT_DIR" -name "*.zip" -type f -mtime +30 -exec rm -v {} \;
printf "Removing ZIP files older than 30 days completed\n"


printf "Backup completed successfully: %s.tar.gz\n" "$NEW_DIR"
