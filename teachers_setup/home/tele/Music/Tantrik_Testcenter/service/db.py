from ..utils.db import get_db_connection
from flask import jsonify


async def find_student_db(rollno) -> dict:
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT rollno, name, course, year, server FROM students WHERE rollno = %s",
                (rollno,),
            )
            student = cursor.fetchone()
        return jsonify({"Error": False, "payload": student})
    except Exception as e:
        return jsonify({"Error": True, "message": str(e)})


async def insert_update_student_db(rollno, name, course, year, server) -> dict:
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                    INSERT INTO students (rollno, name, course, year, server)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=VALUES(name), course=VALUES(course), year=VALUES(year), server=VALUES(server);
                """,
                (rollno, name, course, year, server),
            )

        return jsonify({"Error": False, "message": "Updated student in DB."})
    except Exception as e:
        return jsonify({"Error": True, "message": str(e)})