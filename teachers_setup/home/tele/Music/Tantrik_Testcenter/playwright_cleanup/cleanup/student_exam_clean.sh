#!/bin/bash

cleanup_files() {
    local user="$1"
    local course="$2"
    local student_dir="/home/$user/$course"

    echo "Processing user: $user for course: $course" >>"$OUTPUT_FILE"
    echo "1. Started cleaning up directory: $student_dir of student: $user for course: $course" >>"$OUTPUT_FILE"
    # Clean up student directory
    if [[ -d "$student_dir" ]]; then
        rm -rf "$student_dir" && echo "Successfully removed folder for user $user from home directory." >>"$OUTPUT_FILE" || echo "Failed to remove files in $student_dir directory, skipping..." >>"$OUTPUT_FILE"
    else
        echo "Folder for user $user not found in home directory, skipping..." >>"$OUTPUT_FILE"
    fi

    # cleanup student feadbacks
    local submitted_dir="/home/$user/.local/share/jupyter/nbgrader_cache/$course"
    echo "2. Started cleaning up submissions of student: $user for course: $course folder: $submitted_dir" >>"$OUTPUT_FILE"
    if [[ -d "$submitted_dir" ]]; then
        rm -rf "$submitted_dir" && echo "Successfully removed submissions of student: $user" >>"$OUTPUT_FILE" || echo "Failed to remove submissions of student $user, skipping..." >>"$OUTPUT_FILE"
    else
        echo "submissions folder of student $user not found, skipping..." >>"$OUTPUT_FILE"
    fi

    local local_instalations="/home/$user/.cache"
    if [[ -d "$local_instalations" ]]; then
        rm -rf "$local_instalations" && echo "Successfully removed local installations folder for user $user from home directory." >>"$OUTPUT_FILE" || echo "Failed to remove local installations folder for user $user from home directory, skipping..." >>"$OUTPUT_FILE"
    fi
}

teacher() {
    local course="$1"
    # Clean up exchange directory
    local exchange_dirs=(
        "/usr/local/share/nbgrader/exchange/$course/inbound"
        "/usr/local/share/nbgrader/exchange/$course/feedback"
    )
    echo "3. Started cleaning up exchange directories: ${exchange_dirs[*]} for course: $course" >>"$OUTPUT_FILE"
    for exchange_dir in "${exchange_dirs[@]}"; do
        if [[ -d "$exchange_dir" ]]; then
            rm -rf "$exchange_dir" || echo "Failed to remove folder in $exchange_dir directory." >>"$OUTPUT_FILE"
        fi
    done
    echo "Successfully cleared exchange folders of student." >>"$OUTPUT_FILE"

    local teacher_dir="/home/grader-$course/$course"
    echo "4. Started cleaning up teacher directory: $teacher_dir of for course: $course" >>"$OUTPUT_FILE"
    if [[ -d "$teacher_dir" ]]; then
        local folders=("autograded" "submitted" "feedback" "source" "release")
        for folder in "${folders[@]}"; do
            echo "* Started clearing student files in $folder directory" >>"$OUTPUT_FILE"
            local delete_path="$teacher_dir/$folder"
            if [[ -d "$delete_path" ]]; then
                rm -rf "$delete_path" && echo "  Successfully removed folder of from teacher directory." >>"$OUTPUT_FILE" || echo "  Failed to remove folder of from teacher $folder directory, skipping..." >>"$OUTPUT_FILE"
            else
                echo "  Student directory not found in $folder folder." >>"$OUTPUT_FILE"
            fi
        done
    else
        echo "Grader directory: $teacher_dir not found, skipping teacher cleanup." >>"$OUTPUT_FILE"
    fi
}

# Main script execution
if [[ -z "$1" ]]; then
    echo "Usage: $0 <users_file> <course> <user> <password> <ip_address>" >>"$OUTPUT_FILE"
    exit 1
fi

USERS_FILE="$1"
COURSE="$2"
OUTPUT_FILE="$3"

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
    teacher "$COURSE"
} <"$USERS_FILE"
