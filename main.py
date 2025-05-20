import sys
import mariadb
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, time
from database import Database

app = Flask(__name__)
app.secret_key = "classroom_management_secret_key"

# Database connection configuration
db_config = {
    "user": "root",
    "password": " ",
    "host": "localhost",
    "database": "classroom_management",
    "port": 3306
}

# Create database instance
db_manager = Database(db_config,reset=False, sample_bookings=True)

# Function to establish database connection
def get_db_connection():
    return db_manager.get_connection()




# Flask routes remain the same as in your original code
@app.route('/')
def index():
    return render_template('index.html')

# Other routes...

@app.route('/classrooms')
def classrooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
    SELECT c.classroom_id, c.room_number, b.building_name, c.capacity, c.floor_number, c.is_lab
    FROM Classrooms c
    JOIN Buildings b ON c.building_id = b.building_id
    ORDER BY b.building_name, c.room_number
    """)
    
    classroom_list = cursor.fetchall()
    
    # Get features for each classroom
    for classroom in classroom_list:
        cursor.execute("""
        SELECT f.feature_name
        FROM ClassroomFeaturesMapping m
        JOIN ClassroomFeatures f ON m.feature_id = f.feature_id
        WHERE m.classroom_id = ?
        """, (classroom['classroom_id'],))
        
        features = cursor.fetchall()
        classroom['features'] = [feature['feature_name'] for feature in features]
    
    cursor.close()
    conn.close()
    
    return render_template('classrooms.html', classrooms=classroom_list)

@app.route('/find_available_classrooms', methods=['GET', 'POST'])
def find_available_classrooms():
    if request.method == 'POST':
        day_id = request.form.get('day_id')
        slot_id = request.form.get('slot_id')
        capacity = request.form.get('capacity', 0)
        is_lab = 1 if request.form.get('is_lab') == 'on' else 0
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.callproc('FindAvailableClassrooms', (day_id, slot_id, capacity, is_lab))
            available_classrooms = cursor.fetchall()
            
            cursor.execute("SELECT day_id, day_name FROM Days")
            days = cursor.fetchall()
            
            cursor.execute("SELECT slot_id, slot_name, start_time, end_time FROM TimeSlots")
            time_slots = cursor.fetchall()
            
            return render_template('available_classrooms.html',
                                  classrooms=available_classrooms,
                                  days=days,
                                  time_slots=time_slots,
                                  selected_day=int(day_id),
                                  selected_slot=int(slot_id),
                                  capacity=capacity,
                                  is_lab=is_lab)
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for('find_available_classrooms'))
        finally:
            cursor.close()
            conn.close()
    else:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT day_id, day_name FROM Days")
        days = cursor.fetchall()
        
        cursor.execute("SELECT slot_id, slot_name, start_time, end_time FROM TimeSlots")
        time_slots = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('find_classroom.html', days=days, time_slots=time_slots)

@app.route('/faculty_schedule')
def faculty_schedule():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT faculty_id, CONCAT(first_name, ' ', last_name) as full_name FROM Faculty ORDER BY last_name, first_name")
    faculty_list = cursor.fetchall()
    
    faculty_id = request.args.get('faculty_id')
    if faculty_id:
        cursor.execute("""
        SELECT fs.day_name, fs.slot_name, fs.start_time, fs.end_time,
               fs.room_number, fs.building_name, fs.course_code, fs.course_name
        FROM FacultySchedule fs
        WHERE fs.faculty_id = ?
        ORDER BY FIELD(fs.day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
                 fs.start_time
        """, (faculty_id,))
        
        schedule = cursor.fetchall()
        
        cursor.execute("""
        SELECT CONCAT(first_name, ' ', last_name) as faculty_name
        FROM Faculty
        WHERE faculty_id = ?
        """, (faculty_id,))
        
        faculty_name = cursor.fetchone()['faculty_name']
    else:
        schedule = []
        faculty_name = None
    
    cursor.close()
    conn.close()
    
    return render_template('faculty_schedule.html',
                          faculty_list=faculty_list,
                          selected_faculty=int(faculty_id) if faculty_id else None,
                          faculty_name=faculty_name,
                          schedule=schedule)

@app.route('/book_classroom', methods=['GET', 'POST'])
def book_classroom():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        classroom_id = request.form.get('classroom_id')
        faculty_id = request.form.get('faculty_id')
        course_id = request.form.get('course_id')
        day_id = request.form.get('day_id')
        slot_id = request.form.get('slot_id')
        semester = request.form.get('semester')
        academic_year = request.form.get('academic_year')
        
        try:
            cursor.execute("""
            INSERT INTO Bookings (classroom_id, faculty_id, course_id, day_id, slot_id, semester, academic_year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (classroom_id, faculty_id, course_id, day_id, slot_id, semester, academic_year))
            
            conn.commit()
            flash("Classroom booked successfully!", "success")
            return redirect(url_for('bookings'))
        except mariadb.Error as e:
            conn.rollback()
            flash(f"Error booking classroom: {e}", "danger")
    
    # Get data for form dropdowns
    cursor.execute("""
    SELECT c.classroom_id, CONCAT(c.room_number, ' (', b.building_name, ')') as classroom_name
    FROM Classrooms c
    JOIN Buildings b ON c.building_id = b.building_id
    ORDER BY b.building_name, c.room_number
    """)
    classrooms = cursor.fetchall()
    
    cursor.execute("""
    SELECT faculty_id, CONCAT(first_name, ' ', last_name) as faculty_name
    FROM Faculty
    ORDER BY last_name, first_name
    """)
    faculty = cursor.fetchall()
    
    cursor.execute("""
    SELECT course_id, CONCAT(course_code, ' - ', course_name) as course_title
    FROM Courses
    ORDER BY course_code
    """)
    courses = cursor.fetchall()
    
    cursor.execute("SELECT day_id, day_name FROM Days")
    days = cursor.fetchall()
    
    cursor.execute("SELECT slot_id, CONCAT(slot_name, ' (', start_time, '-', end_time, ')') as time_slot FROM TimeSlots")
    time_slots = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('book_classroom.html',
                          classrooms=classrooms,
                          faculty=faculty,
                          courses=courses,
                          days=days,
                          time_slots=time_slots)

@app.route('/bookings')
def bookings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
    SELECT b.booking_id, d.day_name, t.slot_name, t.start_time, t.end_time,
           CONCAT(c.room_number, ' (', bld.building_name, ')') as classroom,
           CONCAT(f.first_name, ' ', f.last_name) as faculty_name,
           cr.course_code, cr.course_name, b.semester, b.academic_year, b.status
    FROM Bookings b
    JOIN Days d ON b.day_id = d.day_id
    JOIN TimeSlots t ON b.slot_id = t.slot_id
    JOIN Classrooms c ON b.classroom_id = c.classroom_id
    JOIN Buildings bld ON c.building_id = bld.building_id
    JOIN Faculty f ON b.faculty_id = f.faculty_id
    JOIN Courses cr ON b.course_id = cr.course_id
    ORDER BY b.academic_year DESC, b.semester, d.day_id, t.start_time
    """)
    
    booking_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('bookings.html', bookings=booking_list)

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/api/classroom_usage')
def classroom_usage_api():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
    SELECT CONCAT(c.room_number, ' (', b.building_name, ')') as classroom,
           COUNT(bk.booking_id) as booking_count
    FROM Classrooms c
    JOIN Buildings b ON c.building_id = b.building_id
    LEFT JOIN Bookings bk ON c.classroom_id = bk.classroom_id AND bk.status = 'confirmed'
    GROUP BY c.classroom_id
    ORDER BY booking_count DESC
    LIMIT 10
    """)
    
    data = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(data)

@app.route('/api/faculty_load')
def faculty_load_api():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
    SELECT CONCAT(f.first_name, ' ', f.last_name) as faculty_name,
           COUNT(b.booking_id) as class_count
    FROM Faculty f
    LEFT JOIN Bookings b ON f.faculty_id = b.faculty_id AND b.status = 'confirmed'
    GROUP BY f.faculty_id
    ORDER BY class_count DESC
    LIMIT 10
    """)
    
    data = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(data)

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')


@app.route('/admin/reset-database', methods=['POST'])
def reset_database():
    """Admin route to reset the database."""
    try:
        db_manager.reset_database()
        flash("Database has been reset successfully!", "success")
    except Exception as e:
        flash(f"Error resetting database: {e}", "danger")
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Setup database on startup
    db_manager.setup_database()
    app.run(debug=True)
