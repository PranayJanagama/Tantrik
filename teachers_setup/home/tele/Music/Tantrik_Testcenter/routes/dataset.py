import os
import subprocess
from flask import flash, jsonify, redirect, render_template, request
import zipfile
import rarfile
from werkzeug.utils import secure_filename

from ..service.test_center import get_unique_courses, list_folders_files
from ..utils.helpers import allowed_file, decrypt, get_dataset_folder, get_max_content_length, get_testsecter_admin, is_valid_user_token

def init_dataset_page_routes(app):
    @app.route('/datasetpage')
    async def dataset_page():
        try:
            print(request)
            access_token = request.cookies.get('access_token')
            print(access_token)
            if not access_token:
                return jsonify({"error": "Unauthorized access"}), 500
            exists = await is_valid_user_token(access_token)
            if not exists:
                return jsonify({"error": "Unauthorized access"}), 500
            admin = get_testsecter_admin()
            if access_token == admin:
                user = admin
            else:
                user = await decrypt(access_token)
            return render_template('datasets.html', token= access_token, user= user)
        except Exception as e:
            return render_template('datasets.html', user="", token="")
        
    @app.route('/datasets')
    async def datasets():
        user = request.args.get('user')
        admin = get_testsecter_admin()
        if user == admin:
            unique_courses =await get_unique_courses(admin)
        else:
            unique_courses =await get_unique_courses(user)
            
        folders_files =await list_folders_files(unique_courses)
        
        return  jsonify(files=folders_files, courses = unique_courses)
    
    
    @app.route('/uploaddataset', methods=['POST'])
    def upload_dataset_course():
        course_name = request.form['course_name']
        if 'datasets' not in request.files:
            flash('No file part')
            return redirect('/manageusers')
        files = request.files.getlist('datasets')
        folder = get_dataset_folder()
        if not os.path.exists(folder):
            os.mkdir(folder)
        course_folder = os.path.join(folder, course_name)  # Create the course folder
        if not os.path.exists(course_folder):
            os.mkdir(course_folder)
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                file.stream.seek(0, os.SEEK_END)  # Move to end of file
                file_size = file.stream.tell()    # Get size in bytes
                file.stream.seek(0)               # Reset pointer to start
                max_content_length = get_max_content_length()
                if file_size > max_content_length:
                    response = {
                        "message": f"File {filename} exceeds maximum size ({max_content_length}MB).",
                        "redirect_url": "/datasetpage"
                    }
                    return jsonify(response), 400
    
                zip_path = os.path.join(course_folder, filename)  # Save file in course folder
                file.save(zip_path)
                try:
                    if zipfile.is_zipfile(zip_path):
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(course_folder)
                    elif rarfile.is_rarfile(zip_path):
                        with rarfile.RarFile(zip_path, 'r') as rar_ref:
                            rar_ref.extractall(course_folder)
                    flash(f'File {filename} uploaded and extracted successfully.')
                except Exception as e:
                    response = {
                        "message": f'An error occurred while extracting {filename}: {str(e)}',
                        "redirect_url": "/datasetpage"
                    }
                    return jsonify(response)
                finally:
                    command = f"chmod -R 755 {course_folder}"
                    subprocess.run(command, shell=True)
                    os.remove(zip_path)
        response = {
            "message": "datasets uploaded successfully",
            "redirect_url": "/datasetpage"
        }
        return jsonify(response)