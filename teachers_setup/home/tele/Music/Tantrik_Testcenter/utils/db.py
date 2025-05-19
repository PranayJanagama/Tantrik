from flask_mysqldb import MySQL

mysql = MySQL()

def init_app(app):
    mysql.init_app(app)

def get_db_connection():
    try:
        conn = mysql.connection
        if not conn:
            raise RuntimeError("MySQL connection is None.")
        return conn
    except Exception as e:
        raise RuntimeError("Database connection is not initialized.") from e


def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create table queries
    create_scores_table = """
    CREATE TABLE IF NOT EXISTS scores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student VARCHAR(50) NOT NULL,
        StudentName VARCHAR(50) NOT NULL,
        course VARCHAR(50) NOT NULL,
        assignment VARCHAR(50) NOT NULL,
        timestamp VARCHAR(50) NOT NULL,
        score VARCHAR(50) NOT NULL,
        submited_on VARCHAR(50) NOT NULL,
        createdon DATETIME(6) DEFAULT current_timestamp(6),
        updatedon DATETIME(6) DEFAULT current_timestamp(6) ON UPDATE current_timestamp(6),
        UNIQUE KEY (student, course, assignment)
    );"""
    
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
       id INT AUTO_INCREMENT PRIMARY KEY,
       username VARCHAR(50) NOT NULL,
       token VARCHAR(255) NOT NULL,
       created_at DATETIME,
       updated_at DATETIME,
       createdon DATETIME(6) DEFAULT current_timestamp(6),
       updatedon DATETIME(6) DEFAULT current_timestamp(6) ON UPDATE current_timestamp(6),
       UNIQUE KEY ( username )
    )
    """
    create_instructor_courses_table = """
    CREATE TABLE IF NOT EXISTS instructor_courses (
       id INT AUTO_INCREMENT PRIMARY KEY,
       instructor VARCHAR(50) NOT NULL,
       course VARCHAR(505) NOT NULL,
       created_at DATETIME,
       updated_at DATETIME,
       createdon DATETIME(6) DEFAULT current_timestamp(6),
       updatedon DATETIME(6) DEFAULT current_timestamp(6) ON UPDATE current_timestamp(6),
       UNIQUE KEY ( instructor, course )
    )
    """
    create_student_courses_table = """
    CREATE TABLE IF NOT EXISTS student_courses (
       id INT AUTO_INCREMENT PRIMARY KEY,
       student VARCHAR(50) NOT NULL,
       course VARCHAR(505) NOT NULL,
       created_at DATETIME,
       updated_at DATETIME,
       createdon DATETIME(6) DEFAULT current_timestamp(6),
       updatedon DATETIME(6) DEFAULT current_timestamp(6) ON UPDATE current_timestamp(6),
       UNIQUE KEY ( student, course )
    )
    """
    create_courses_table = """
    CREATE TABLE IF NOT EXISTS course (
       id INT AUTO_INCREMENT PRIMARY KEY,
       name VARCHAR(50) NOT NULL,
       created_at DATETIME,
       updated_at DATETIME,
       createdon DATETIME(6) DEFAULT current_timestamp(6),
       updatedon DATETIME(6) DEFAULT current_timestamp(6) ON UPDATE current_timestamp(6),
       UNIQUE KEY ( name )
    )
    """
    create_students_table = """
    CREATE TABLE IF NOT EXISTS students (
       id INT AUTO_INCREMENT PRIMARY KEY,
       rollno VARCHAR(50) NOT NULL,
       name VARCHAR(50) NOT NULL,
       createdon DATETIME(6) DEFAULT current_timestamp(6),
       updatedon DATETIME(6) DEFAULT current_timestamp(6) ON UPDATE current_timestamp(6),
       UNIQUE KEY ( rollno )
    )
    """

    # Execute queries
    cursor.execute(create_scores_table)
    cursor.execute(create_users_table)
    cursor.execute(create_instructor_courses_table)
    cursor.execute(create_student_courses_table)
    cursor.execute(create_courses_table)
    cursor.execute(create_students_table)
    cursor.execute("""
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'scores'
      AND COLUMN_NAME = 'server'
      AND TABLE_SCHEMA = DATABASE();
    """)

    column_exists = cursor.fetchone()[0]

    if column_exists == 0:
        cursor.execute("""
        ALTER TABLE scores ADD COLUMN server INT;
        """)
    cursor.execute("""
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'students'
      AND COLUMN_NAME = 'course'
      AND TABLE_SCHEMA = DATABASE();
    """)
    column_exists = cursor.fetchone()[0]

    if column_exists == 0:
        cursor.execute("""
        ALTER TABLE students ADD COLUMN course VARCHAR(50);
        """)
    cursor.execute("""
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'students'
      AND COLUMN_NAME = 'year'
      AND TABLE_SCHEMA = DATABASE();
    """)
    column_exists = cursor.fetchone()[0]

    if column_exists == 0:
        cursor.execute("""
        ALTER TABLE students ADD COLUMN year INT;
        """)

    cursor.execute("""
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'students'
      AND COLUMN_NAME = 'server'
      AND TABLE_SCHEMA = DATABASE();
    """)
    column_exists = cursor.fetchone()[0]

    if column_exists == 0:
        cursor.execute("""
        ALTER TABLE students ADD COLUMN server VARCHAR(5) DEFAULT NULL;
        """)
    conn.commit()
    cursor.close()
