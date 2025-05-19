from datetime import datetime
from flask import request, jsonify, render_template

from ..utils.db import get_db_connection
from ..utils.helpers import is_valid_user_token, decrypt

def init_student_report_routes(app):
    @app.route('/studentreport')
    async def studentreport():
        user_token = request.query_string.decode("utf-8").replace("access_token=", "")
        if user_token == '':
             return jsonify({"error": "Unauthorized access"}), 500
        exists = await is_valid_user_token(user_token)
        if exists == False:
            return jsonify({"error": "Unauthorized access"}), 500
        student = await decrypt(user_token)
        stu_payload = {
            "rollno": student,
            "name": student,
            "course":"course101"
        }
        try:
            with get_db_connection().cursor as cursor:
                cursor.execute("""
                            select course, name from students where rollno = %s
                            """, (student))
                stu_data = cursor.fetchone()
                if stu_data is not None:
                    stu_payload["course"] = stu_data[0]
                    stu_payload["name"] = stu_data[1]
                    return render_template('studentrecords.html', payload = stu_payload)
                else:
                    return render_template('studentrecords.html', payload = stu_payload)
        except Exception as e:
            return render_template('studentrecords.html', payload = stu_payload)
    
    @app.route('/get_submissions')
    def get_submissions():
        course_name = request.args.get("course_name")
        rollno = request.form.get("rollno")
        try:
            data = []
            with get_db_connection().cursor() as cursor:
                cursor.execute("SELECT assignment, score, submited_on FROM scores s WHERE student = %s AND s.course =%s assignment NOT LIKE '%%Practice%%' AND assignment NOT LIKE '%%practice%%' AND assignment NOT LIKE '%%Demo%%' AND assignment NOT LIKE '%%demo%%' AND assignment NOT LIKE 'ps1';", (rollno, course_name))
                submissions = cursor.fetchall()
                for submission in submissions:
                    data.append({
                        "assignment":submission[0],
                        "score":submission[1],
                        "submittedon":datetime.strptime(submission[2], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M')
                    })
            return jsonify({"payload": data, "message":"data retrived successfully"})
        except Exception as e:
            return jsonify({"payload": [], "message":"data retrived unsuccessfully", "error":str(e)})