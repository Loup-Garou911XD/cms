import mariadb
import sys
from flask import current_app, g
from datetime import datetime

class Database:
    def __init__(self, config, reset:bool = False, sample_bookings:bool = True):
        """Initialize the Database class with configuration parameters.
        
        Args:
            config (dict): Database configuration dictionary containing user, password, host, database, port
        """
        self.sample_bookings = sample_bookings
        self.config = config
        if reset:
            self.reset_database()

    def get_connection(self):
        """Establish and return a database connection.
        
        Returns:
            connection: MariaDB connection object
        """
        try:
            conn = mariadb.connect(**self.config)
            conn.autocommit = False
            return conn
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB: {e}")
            sys.exit(1)
            
    def setup_database(self):
        """Create the database, tables, views, stored procedures, and insert sample data."""
        # Connect to MariaDB without specifying a database
        try:
            conn = mariadb.connect(
                user=self.config["user"],
                password=self.config["password"],
                host=self.config["host"],
                port=self.config["port"]
            )
            cursor = conn.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
            cursor.execute(f"USE {self.config['database']}")
            
            # Create tables with proper relationships and constraints
            self._create_tables(cursor)
            
            # Create views
            self._create_views(cursor)
            
            # Create stored procedures
            self._create_stored_procedures(cursor)
            
            # Create triggers
            self._create_triggers(cursor)
            
            # Insert sample data
            self._insert_sample_data(cursor)
            
            conn.commit()
            print("Database setup completed successfully!")
        except mariadb.Error as e:
            print(f"Error setting up database: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def reset_database(self):
        """Reset the database by dropping and recreating all tables and data."""
        try:
            conn = mariadb.connect(
                user=self.config["user"],
                password=self.config["password"],
                host=self.config["host"],
                port=self.config["port"]
            )
            cursor = conn.cursor()
            
            # Use the database
            cursor.execute(f"USE {self.config['database']}")
            
            # Disable foreign key checks to avoid constraint errors during drop
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # Drop all tables, views, triggers, and procedures
            print("Dropping existing database objects...")
            
            # Drop tables in reverse order of dependencies
            tables = [
                "BookingAuditLog", "Bookings", "ClassroomFeaturesMapping", 
                "ClassroomFeatures", "TimeSlots", "Days", "Courses", 
                "Faculty", "Classrooms", "Departments", "Buildings"
            ]
            
            for table in tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    print(f"Dropped table {table}")
                except mariadb.Error as e:
                    print(f"Error dropping table {table}: {e}")
            
            # Drop views
            views = ["AvailableClassrooms", "FacultySchedule"]
            for view in views:
                try:
                    cursor.execute(f"DROP VIEW IF EXISTS {view}")
                    print(f"Dropped view {view}")
                except mariadb.Error as e:
                    print(f"Error dropping view {view}: {e}")
            
            # Drop procedures
            procedures = ["FindAvailableClassrooms"]
            for proc in procedures:
                try:
                    cursor.execute(f"DROP PROCEDURE IF EXISTS {proc}")
                    print(f"Dropped procedure {proc}")
                except mariadb.Error as e:
                    print(f"Error dropping procedure {proc}: {e}")
            
            # Drop triggers
            triggers = ["prevent_faculty_double_booking", "booking_status_change"]
            for trigger in triggers:
                try:
                    cursor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
                    print(f"Dropped trigger {trigger}")
                except mariadb.Error as e:
                    print(f"Error dropping trigger {trigger}: {e}")
            
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            conn.commit()
            print("Database reset completed. Recreating database structure...")
            
            # Recreate all tables, views, procedures, and sample data
            self._create_tables(cursor)
            self._create_views(cursor)
            self._create_stored_procedures(cursor)
            self._create_triggers(cursor)
            self._insert_sample_data(cursor)
            
            conn.commit()
            print("Database has been successfully reset and repopulated with sample data!")
            
        except mariadb.Error as e:
            print(f"Error resetting database: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def _create_tables(self, cursor):
        """Create all database tables."""
        # Buildings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Buildings (
            building_id INT AUTO_INCREMENT PRIMARY KEY,
            building_name VARCHAR(100) NOT NULL,
            location VARCHAR(255),
            total_floors INT
        )
        """)
        
        # Departments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Departments (
            dept_id INT AUTO_INCREMENT PRIMARY KEY,
            dept_name VARCHAR(100) NOT NULL,
            dept_code VARCHAR(20) NOT NULL UNIQUE,
            building_id INT,
            FOREIGN KEY (building_id) REFERENCES Buildings(building_id)
        )
        """)
        
        # Classrooms table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Classrooms (
            classroom_id INT AUTO_INCREMENT PRIMARY KEY,
            room_number VARCHAR(20) NOT NULL,
            building_id INT NOT NULL,
            capacity INT NOT NULL,
            is_lab BOOLEAN DEFAULT FALSE,
            floor_number INT,
            FOREIGN KEY (building_id) REFERENCES Buildings(building_id),
            CONSTRAINT unique_room_building UNIQUE (room_number, building_id)
        )
        """)
        
        # Faculty table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Faculty (
            faculty_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE,
            phone VARCHAR(20),
            dept_id INT,
            designation VARCHAR(50),
            FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
        )
        """)
        
        # Courses table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Courses (
            course_id INT AUTO_INCREMENT PRIMARY KEY,
            course_code VARCHAR(20) NOT NULL UNIQUE,
            course_name VARCHAR(100) NOT NULL,
            credits INT,
            dept_id INT,
            requires_lab BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
        )
        """)
        
        # Days table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Days (
            day_id INT AUTO_INCREMENT PRIMARY KEY,
            day_name VARCHAR(20) NOT NULL UNIQUE
        )
        """)
        
        # TimeSlots table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS TimeSlots (
            slot_id INT AUTO_INCREMENT PRIMARY KEY,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            slot_name VARCHAR(20) UNIQUE,
            CONSTRAINT check_times CHECK (start_time < end_time),
            CONSTRAINT unique_time_slot UNIQUE (start_time, end_time)
        )
        """)
        
        # ClassroomFeatures table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ClassroomFeatures (
            feature_id INT AUTO_INCREMENT PRIMARY KEY,
            feature_name VARCHAR(50) NOT NULL UNIQUE,
            description VARCHAR(255)
        )
        """)
        
        # ClassroomFeaturesMapping table (resolves M:N relationship)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ClassroomFeaturesMapping (
            mapping_id INT AUTO_INCREMENT PRIMARY KEY,
            classroom_id INT NOT NULL,
            feature_id INT NOT NULL,
            FOREIGN KEY (classroom_id) REFERENCES Classrooms(classroom_id),
            FOREIGN KEY (feature_id) REFERENCES ClassroomFeatures(feature_id),
            CONSTRAINT unique_feature_mapping UNIQUE (classroom_id, feature_id)
        )
        """)
        
        # Bookings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bookings (
            booking_id INT AUTO_INCREMENT PRIMARY KEY,
            classroom_id INT NOT NULL,
            faculty_id INT NOT NULL,
            course_id INT NOT NULL,
            day_id INT NOT NULL,
            slot_id INT NOT NULL,
            semester VARCHAR(20),
            academic_year VARCHAR(20),
            status ENUM('confirmed', 'pending', 'cancelled') DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (classroom_id) REFERENCES Classrooms(classroom_id),
            FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id),
            FOREIGN KEY (course_id) REFERENCES Courses(course_id),
            FOREIGN KEY (day_id) REFERENCES Days(day_id),
            FOREIGN KEY (slot_id) REFERENCES TimeSlots(slot_id),
            CONSTRAINT unique_booking UNIQUE (classroom_id, day_id, slot_id, academic_year, semester)
        )
        """)
        
        # Create audit log table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS BookingAuditLog (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT,
            action VARCHAR(20),
            old_status VARCHAR(20),
            new_status VARCHAR(20),
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    
    def _create_views(self, cursor):
        """Create database views."""
        # Create view for available classrooms
        cursor.execute("""
        CREATE OR REPLACE VIEW AvailableClassrooms AS
        SELECT c.classroom_id, c.room_number, b.building_name, d.day_name, t.slot_name, t.start_time, t.end_time
        FROM Classrooms c
        CROSS JOIN Days d
        CROSS JOIN TimeSlots t
        JOIN Buildings b ON c.building_id = b.building_id
        WHERE NOT EXISTS (
            SELECT 1 FROM Bookings bk
            WHERE bk.classroom_id = c.classroom_id
            AND bk.day_id = d.day_id
            AND bk.slot_id = t.slot_id
            AND bk.status = 'confirmed'
        )
        """)
        
        # Create view for faculty schedule
        cursor.execute("""
        CREATE OR REPLACE VIEW FacultySchedule AS
        SELECT f.faculty_id, CONCAT(f.first_name, ' ', f.last_name) as faculty_name,
               d.day_name, t.slot_name, t.start_time, t.end_time,
               c.room_number, b.building_name, cr.course_code, cr.course_name
        FROM Bookings bk
        JOIN Faculty f ON bk.faculty_id = f.faculty_id
        JOIN Days d ON bk.day_id = d.day_id
        JOIN TimeSlots t ON bk.slot_id = t.slot_id
        JOIN Classrooms c ON bk.classroom_id = c.classroom_id
        JOIN Buildings b ON c.building_id = b.building_id
        JOIN Courses cr ON bk.course_id = cr.course_id
        WHERE bk.status = 'confirmed'
        """)
    
    def _create_stored_procedures(self, cursor):
        """Create stored procedures."""
        # Create stored procedure to find available classrooms
        cursor.execute("""
        CREATE OR REPLACE PROCEDURE FindAvailableClassrooms(
            IN p_day_id INT,
            IN p_slot_id INT,
            IN p_capacity INT,
            IN p_is_lab BOOLEAN
        )
        BEGIN
            SELECT c.classroom_id, c.room_number, b.building_name, c.capacity, c.floor_number, c.is_lab
            FROM Classrooms c
            JOIN Buildings b ON c.building_id = b.building_id
            WHERE c.capacity >= p_capacity
            AND c.is_lab = p_is_lab
            AND NOT EXISTS (
                SELECT 1 FROM Bookings bk
                WHERE bk.classroom_id = c.classroom_id
                AND bk.day_id = p_day_id
                AND bk.slot_id = p_slot_id
                AND bk.status = 'confirmed'
            )
            ORDER BY c.capacity;
        END
        """)
    
    def _create_triggers(self, cursor):
        """Create database triggers."""

        cursor.execute("""
        CREATE OR REPLACE TRIGGER prevent_faculty_double_booking
        BEFORE INSERT ON Bookings
        FOR EACH ROW
        BEGIN
            DECLARE faculty_exists INT;
            SELECT COUNT(*) INTO faculty_exists
            FROM Bookings
            WHERE faculty_id = NEW.faculty_id
            AND day_id = NEW.day_id
            AND slot_id = NEW.slot_id
            AND status = 'confirmed';
            
            IF faculty_exists > 0 THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Faculty is already booked during this time slot';
            END IF;
        END
        """)
        
        cursor.execute("""
        CREATE OR REPLACE TRIGGER booking_status_change
        AFTER UPDATE ON Bookings
        FOR EACH ROW
        BEGIN
            IF OLD.status != NEW.status THEN
                INSERT INTO BookingAuditLog (booking_id, action, old_status, new_status)
                VALUES (NEW.booking_id, 'UPDATE', OLD.status, NEW.status);
            END IF;
        END
        """)
    
    def _insert_sample_data(self, cursor):
        """Insert sample data into the database."""
        
        cursor.execute("SELECT COUNT(*) FROM Days")
        count = cursor.fetchone()[0]
        if count == 0:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for day in days:
                cursor.execute("INSERT INTO Days (day_name) VALUES (?)", (day,))
        
        # Insert time slots
        cursor.execute("SELECT COUNT(*) FROM TimeSlots")
        count = cursor.fetchone()[0]
        if count == 0:
            time_slots = [
                ("08:00", "09:00", "Period 1"),
                ("09:00", "10:00", "Period 2"),
                ("10:00", "11:00", "Period 3"),
                ("11:00", "12:00", "Period 4"),
                ("12:00", "13:00", "Lunch"),
                ("13:00", "14:00", "Period 5"),
                ("14:00", "15:00", "Period 6"),
                ("15:00", "16:00", "Period 7"),
                ("16:00", "17:00", "Period 8")
            ]
            
            for start, end, name in time_slots:
                cursor.execute("INSERT INTO TimeSlots (start_time, end_time, slot_name) VALUES (?, ?, ?)",
                              (start, end, name))
        
        # Insert sample buildings
        cursor.execute("SELECT COUNT(*) FROM Buildings")
        count = cursor.fetchone()[0]
        if count == 0:
            buildings = [
                ("Main Academic Building", "Central Campus", 4),
                ("Science Block", "North Campus", 3),
                ("Engineering Block", "South Campus", 5),
                ("Library Building", "East Campus", 2)
            ]
            
            for name, location, floors in buildings:
                cursor.execute("INSERT INTO Buildings (building_name, location, total_floors) VALUES (?, ?, ?)",
                              (name, location, floors))
            
            # Get the actual building IDs after insertion
            cursor.execute("SELECT building_id, building_name FROM Buildings")
            building_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Insert sample departments with correct building IDs
            cursor.execute("SELECT COUNT(*) FROM Departments")
            count = cursor.fetchone()[0]
            if count == 0:
                departments = [
                    ("Computer Science", "CSE", building_map["Main Academic Building"]),
                    ("Electronics Engineering", "ECE", building_map["Main Academic Building"]),
                    ("Mechanical Engineering", "ME", building_map["Science Block"]),
                    ("Information Technology", "IT", building_map["Main Academic Building"])
                ]
                
                for name, code, building_id in departments:
                    cursor.execute("INSERT INTO Departments (dept_name, dept_code, building_id) VALUES (?, ?, ?)",
                                  (name, code, building_id))
            
            # Insert sample classrooms with correct building IDs
            cursor.execute("SELECT COUNT(*) FROM Classrooms")
            count = cursor.fetchone()[0]
            if count == 0:
                classrooms = [
                    ("101", building_map["Main Academic Building"], 30, False, 1),
                    ("102", building_map["Main Academic Building"], 45, False, 1),
                    ("103", building_map["Main Academic Building"], 60, False, 1),
                    ("201", building_map["Main Academic Building"], 40, False, 2),
                    ("202", building_map["Main Academic Building"], 50, False, 2),
                    ("Lab-1", building_map["Science Block"], 35, True, 1),
                    ("Lab-2", building_map["Science Block"], 40, True, 1),
                    ("301", building_map["Engineering Block"], 70, False, 3),
                    ("302", building_map["Engineering Block"], 65, False, 3),
                    ("Lab-3", building_map["Engineering Block"], 45, True, 2)
                ]
                
                for room, building_id, capacity, is_lab, floor in classrooms:
                    cursor.execute("INSERT INTO Classrooms (room_number, building_id, capacity, is_lab, floor_number) VALUES (?, ?, ?, ?, ?)",
                                  (room, building_id, capacity, is_lab, floor))
        
        # Insert classroom features
        cursor.execute("SELECT COUNT(*) FROM ClassroomFeatures")
        count = cursor.fetchone()[0]
        if count == 0:
            features = [
                ("Projector", "Digital projector for presentations"),
                ("Smart Board", "Interactive digital whiteboard"),
                ("AC", "Air conditioning"),
                ("Computer Terminals", "Desktop computers for each student"),
                ("Audio System", "Sound system for multimedia presentations")
            ]
            
            for name, description in features:
                cursor.execute("INSERT INTO ClassroomFeatures (feature_name, description) VALUES (?, ?)",
                              (name, description))
        
        # Map features to classrooms
        cursor.execute("SELECT COUNT(*) FROM ClassroomFeaturesMapping")
        count = cursor.fetchone()[0]
        if count == 0:
            # Get the actual classroom IDs
            cursor.execute("SELECT classroom_id, room_number FROM Classrooms")
            classroom_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Get the actual feature IDs
            cursor.execute("SELECT feature_id, feature_name FROM ClassroomFeatures")
            feature_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            mappings = [
                (classroom_map["101"], feature_map["Projector"]), 
                (classroom_map["101"], feature_map["AC"]), 
                (classroom_map["102"], feature_map["Smart Board"]), 
                (classroom_map["103"], feature_map["Projector"]), 
                (classroom_map["103"], feature_map["AC"]),
                (classroom_map["Lab-1"], feature_map["Computer Terminals"]), 
                (classroom_map["Lab-2"], feature_map["Computer Terminals"]), 
                (classroom_map["301"], feature_map["Audio System"]), 
                (classroom_map["302"], feature_map["Projector"]), 
                (classroom_map["Lab-3"], feature_map["AC"])
            ]
            
            for classroom_id, feature_id in mappings:
                cursor.execute("INSERT INTO ClassroomFeaturesMapping (classroom_id, feature_id) VALUES (?, ?)",
                              (classroom_id, feature_id))
        
        # Get department IDs
        cursor.execute("SELECT dept_id, dept_code FROM Departments")
        dept_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        # Insert sample faculty
        cursor.execute("SELECT COUNT(*) FROM Faculty")
        count = cursor.fetchone()[0]
        if count == 0:
            faculty = [
                ("John", "Doe", "john.doe@university.edu", "555-1234", dept_map["CSE"], "Professor"),
                ("Jane", "Smith", "jane.smith@university.edu", "555-2345", dept_map["CSE"], "Assistant Professor"),
                ("Robert", "Johnson", "robert.johnson@university.edu", "555-3456", dept_map["ECE"], "Associate Professor"),
                ("Sarah", "Williams", "sarah.williams@university.edu", "555-4567", dept_map["ECE"], "Professor"),
                ("Michael", "Brown", "michael.brown@university.edu", "555-5678", dept_map["ME"], "Assistant Professor"),
                ("Emily", "Davis", "emily.davis@university.edu", "555-6789", dept_map["ME"], "Lecturer"),
                ("David", "Miller", "david.miller@university.edu", "555-7890", dept_map["IT"], "Professor"),
                ("Lisa", "Wilson", "lisa.wilson@university.edu", "555-8901", dept_map["IT"], "Associate Professor")
            ]
            
            for fname, lname, email, phone, dept_id, designation in faculty:
                cursor.execute("INSERT INTO Faculty (first_name, last_name, email, phone, dept_id, designation) VALUES (?, ?, ?, ?, ?, ?)",
                              (fname, lname, email, phone, dept_id, designation))
        
        # Insert sample courses
        cursor.execute("SELECT COUNT(*) FROM Courses")
        count = cursor.fetchone()[0]
        if count == 0:
            courses = [
                ("CS101", "Introduction to Programming", 3, dept_map["CSE"], False),
                ("CS201", "Data Structures", 4, dept_map["CSE"], False),
                ("CS301", "Database Systems", 4, dept_map["CSE"], True),
                ("EC101", "Electronic Circuits", 3, dept_map["ECE"], False),
                ("EC201", "Signal Processing", 4, dept_map["ECE"], True),
                ("ME101", "Engineering Mechanics", 3, dept_map["ME"], False),
                ("ME201", "Thermodynamics", 4, dept_map["ME"], False),
                ("IT101", "Information Systems", 3, dept_map["IT"], False),
                ("IT201", "Web Technologies", 4, dept_map["IT"], True)
            ]
            
            for code, name, credits, dept_id, lab in courses:
                cursor.execute("INSERT INTO Courses (course_code, course_name, credits, dept_id, requires_lab) VALUES (?, ?, ?, ?, ?)",
                              (code, name, credits, dept_id, lab))
        
        # Get faculty, course, and classroom IDs for bookings
        cursor.execute("SELECT faculty_id, email FROM Faculty")
        faculty_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        cursor.execute("SELECT course_id, course_code FROM Courses")
        course_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        # Insert some sample bookings
        cursor.execute("SELECT COUNT(*) FROM Bookings")
        count = cursor.fetchone()[0]
        if count == 0:
            # Get classroom IDs
            cursor.execute("SELECT classroom_id, room_number FROM Classrooms")
            classroom_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Just a few sample bookings to demonstrate
            bookings = [
                (classroom_map["101"], faculty_map["john.doe@university.edu"], course_map["CS101"], 1, 1, "Spring", "2025"),  # Monday, Period 1
                (classroom_map["102"], faculty_map["jane.smith@university.edu"], course_map["CS201"], 2, 2, "Spring", "2025"),  # Tuesday, Period 2
                (classroom_map["Lab-1"], faculty_map["robert.johnson@university.edu"], course_map["CS301"], 3, 5, "Spring", "2025"),  # Wednesday, Period 5
                (classroom_map["Lab-2"], faculty_map["sarah.williams@university.edu"], course_map["EC201"], 4, 6, "Spring", "2025"),  # Thursday, Period 6
                (classroom_map["301"], faculty_map["michael.brown@university.edu"], course_map["ME101"], 5, 3, "Spring", "2025")  # Friday, Period 3
            ]
            if self.sample_bookings:
                for classroom_id, faculty_id, course_id, day_id, slot_id, semester, year in bookings:
                    cursor.execute("""
                    INSERT INTO Bookings
                    (classroom_id, faculty_id, course_id, day_id, slot_id, semester, academic_year)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (classroom_id, faculty_id, course_id, day_id, slot_id, semester, year))
