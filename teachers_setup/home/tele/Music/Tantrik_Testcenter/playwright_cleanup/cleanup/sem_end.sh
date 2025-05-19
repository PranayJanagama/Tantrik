#!/bin/bash

cleanup_files() {
    local user="$1"
    local course="$2"
    local student_dir="/home/$user/$course"

    echo "Processing user: $user for course: $course" >>"$OUTPUT_FILE"
    echo "1. Started cleaning up directory: $student_dir of student: $user for course: $course" >>"$OUTPUT_FILE"
    # Clean up student directory
    if [[ -d "$student_dir" ]]; then
        rm -rf "${student_dir:?}/"* && echo "Successfully removed folder for user $user from home directory." >>"$OUTPUT_FILE" || echo "Failed to remove files in $student_dir directory, skipping..." >>"$OUTPUT_FILE"
    else
        echo "Folder for user $user not found in home directory $student_dir, skipping..." >>"$OUTPUT_FILE"
    fi

    local local_instalations="/home/$user/.cache"
    echo "2. Started cleaning up local installations folder for user: $user from home directory: $local_instalations" >>"$OUTPUT_FILE"
    if [[ -d "$local_instalations" ]]; then
        rm -rf "$local_instalations" && echo "Successfully removed local installations folder for user $user from home directory." >>"$OUTPUT_FILE" || echo "Failed to remove local installations folder for user $user from home directory, skipping..." >>"$OUTPUT_FILE"
    fi

    local submitted_dir="/home/$user/.local/share/jupyter/nbgrader_cache/$course"
    echo "3. Started cleaning up submissions of student: $user for course: $course folder: $submitted_dir" >>"$OUTPUT_FILE"
    if [[ -d "$submitted_dir" ]]; then
        rm -rf "$submitted_dir" && echo "Successfully removed submissions of student: $user" >>"$OUTPUT_FILE" || echo "Failed to remove submissions of student $user, skipping..." >>"$OUTPUT_FILE"
    else
        echo "submissions folder of student $user not found, skipping..." >>"$OUTPUT_FILE"
    fi

    # Clean up teacher directories
    local teacher_dir="/home/grader-$course/$course"
    echo "4. Started cleaning up teacher directory: $teacher_dir of student: $user for course: $course" >>"$OUTPUT_FILE"
    if [[ -d "$teacher_dir" ]]; then
        local folders=("autograded" "submitted" "feedback" "source" "release")
        for folder in "${folders[@]}"; do
            echo "* Started clearing student files in $folder directory" >>"$OUTPUT_FILE"
            local delete_path="$teacher_dir/$folder/$user"
            if [[ -d "$delete_path" ]]; then
                rm -rf "$delete_path" && echo "  Successfully removed folder of user $user from teacher directory." >>"$OUTPUT_FILE" || echo "  Failed to remove folder of user $user from teacher $folder directory, skipping..." >>"$OUTPUT_FILE"
            elif [[ $folder == "source" || $folder == "release" ]]; then
                local dir="$teacher_dir/$folder/"
                rm -rf "${dir:?}/"* && echo "  Successfully cleaned folder $folder from teacher directory $teacher_dir/$folder/*." >>"$OUTPUT_FILE" \
                || echo "  Failed to remove folder $folder from teacher $folder directory, skipping..." >>"$OUTPUT_FILE"
            else
                echo "  Student directory not found in $folder folder." >>"$OUTPUT_FILE"
            fi
        done
    else
        echo "Grader directory: $teacher_dir not found, skipping teacher cleanup." >>"$OUTPUT_FILE"
    fi

    # Clean up exchange directory
    local exchange_dirs=(
        "/usr/local/share/nbgrader/exchange/$course/inbound"
        "/usr/local/share/nbgrader/exchange/$course/feedback"
    )
    echo "5. Started cleaning up exchange directories: ${exchange_dirs[*]} of student: $user for course: $course" >>"$OUTPUT_FILE"
    for exchange_dir in "${exchange_dirs[@]}"; do
        for dir in $(find "$exchange_dir" -maxdepth 1 -type d -name "$user*" -print); do
            rm -rf "$dir" || echo "Failed to remove folder in $exchange_dir directory." >>"$OUTPUT_FILE"
        done
    done
    echo "Successfully cleared exchange folders of student." >>"$OUTPUT_FILE"

    # Database cleanup
    local db_path="/home/grader-$course/$course/gradebook.db"
    echo "6. Started cleaning up gradebook path: $db_path for student: $user in course: $course" >>"$OUTPUT_FILE"
    teacher_gradebook_clean_user "$user" "$course" "$db_path"
    echo "Successfully cleared gradebook data of student." >>"$OUTPUT_FILE"
    echo "Processing user: $user for course: $course has been completed." >>"$OUTPUT_FILE"
}

teacher_gradebook_clean_user() {
    echo "Cleaning up gradebook of student: $1 in course: $2" >>"$OUTPUT_FILE"
    local user="$1"
    local course="$2"
    local db_path="$3"
    sqlite3 "$db_path" "DELETE FROM comment WHERE notebook_id IN (SELECT sn.id FROM submitted_notebook sn JOIN submitted_assignment sa ON sa.id = sn.assignment_id JOIN assignment a ON a.id = sa.assignment_id WHERE sa.student_id = '$user' AND a.course_id = '$course');"
    sqlite3 "$db_path" "DELETE FROM grade WHERE notebook_id IN (SELECT sn.id FROM submitted_notebook sn JOIN submitted_assignment sa ON sa.id = sn.assignment_id JOIN assignment a ON a.id = sa.assignment_id WHERE sa.student_id = '$user' AND a.course_id = '$course');"
    sqlite3 "$db_path" "DELETE FROM submitted_notebook WHERE assignment_id IN (SELECT sa.id FROM submitted_assignment sa JOIN assignment a ON a.id = sa.assignment_id WHERE sa.student_id = '$user' AND a.course_id = '$course');"
    sqlite3 "$db_path" "DELETE FROM submitted_assignment WHERE assignment_id IN (SELECT id FROM assignment WHERE course_id = '$course') AND student_id = '$user';"
    echo "Successfully cleaned up gradebook of student: $user in course: $course" >>"$OUTPUT_FILE"
}

jh_unenroll_user_group() {
    local user="$1"
    local course="$2"
    local db_path="$3"
    local group="nbgrader-$course"
    echo "Unenrolling user $user from group $group" >>"$OUTPUT_FILE"
    sqlite3 "$db_path" "DELETE FROM user_group_map WHERE user_id IN (SELECT id FROM users WHERE name = '$user') AND group_id IN (SELECT id FROM groups WHERE name = '$group');"
    sqlite3 "$db_path" "DELETE FROM user_role_map WHERE user_id IN (SELECT id FROM users WHERE name = '$user') AND role_id IN (SELECT id FROM roles WHERE name = '$group');"
    echo "Successfully unenrolled user $1 from group nbgrader-$2" >>"$OUTPUT_FILE"
}

# Main script execution
if [[ -z "$1" ]]; then
    echo "Usage: $0 <users_file> <course> <user> <password> <ip_address>" >>"$OUTPUT_FILE"
    exit 1
fi

USERS_FILE="$1"
COURSE="$2"
OUTPUT_FILE="$4"

if [[ ! -f "$USERS_FILE" ]]; then
    echo "Error: File $USERS_FILE not found!" >>"$OUTPUT_FILE"
    exit 2
fi

{
    read -r header_line                        # Read the first line (header)
    IFS=',' read -ra headers <<<"$header_line" # Split headers into an array

    # Read the rest of the file
    while IFS=',' read -r username || [[ -n "$username" ]]; do
        user=$(echo "$username" | tr -d '\n' | xargs)
        if [[ -z "$user" ]]; then
            continue
        fi
        cleanup_files "$user" "$COURSE"
        echo "========================================================================================" >>"$OUTPUT_FILE"
    done
} <"$USERS_FILE"
echo "Processing for course: $COURSE has been completed." >>"$OUTPUT_FILE"