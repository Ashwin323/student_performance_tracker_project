import mysql.connector
from mysql.connector import errorcode
import tkinter as tk
from tkinter import messagebox, ttk
from functools import partial

# Database configuration
db_config = {
    'user': 'root',        # Replace with your MySQL username
    'password': 'ankanjason',    # Replace with your MySQL password
    'host': 'localhost',
    'database': 'studentperformancetracker'
}

# Database setup and connection

def connect_to_db():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Error: Incorrect username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Error: Database does not exist")
        else:
            print(err)
        return None

# Database and table setup with triggers
def setup_database():
    connection = connect_to_db()
    if connection is None:
        temp_connection = mysql.connector.connect(
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host']
        )
        temp_cursor = temp_connection.cursor()
        try:
            temp_cursor.execute("CREATE DATABASE IF NOT EXISTS studentperformancetracker")
            print("Database created or already exists.")
        except mysql.connector.Error as err:
            print(f"Error creating database: {err}")
        finally:
            temp_cursor.close()
            temp_connection.close()
        
        connection = connect_to_db()
        if connection is None:
            print("Error: Could not connect to the newly created database.")
            return
    
    cursor = connection.cursor()
    try:
        cursor.execute("USE studentperformancetracker")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Student (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                date_of_birth DATE,
                email VARCHAR(100) UNIQUE,
                enrollment_year INT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Course (
                course_id INT AUTO_INCREMENT PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL,
                instructor VARCHAR(100),
                schedule VARCHAR(50)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Grades (
                grade_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                course_id INT,
                grade CHAR(2),
                grade_date DATE,
                FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES Course(course_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Attendance (
                attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                course_id INT,
                attendance_date DATE,
                status ENUM('Present', 'Absent', 'Late') DEFAULT 'Present',
                FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES Course(course_id) ON DELETE CASCADE
            );
        """)

        # Create the triggers
        # Trigger to automatically set grade_date on insert
        cursor.execute("""
            CREATE TRIGGER before_insert_grade_date
            BEFORE INSERT ON Grades
            FOR EACH ROW
            SET NEW.grade_date = IFNULL(NEW.grade_date, CURDATE());
        """)

        # Example trigger: Update attendance rate in Student_Performance after attendance update
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Student_Performance (
                student_id INT PRIMARY KEY,
                attendance_rate FLOAT DEFAULT 0.0,
                FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TRIGGER after_update_attendance
            AFTER UPDATE ON Attendance
            FOR EACH ROW
            BEGIN
                DECLARE total INT;
                DECLARE present INT;
                SET total = (SELECT COUNT(*) FROM Attendance WHERE student_id = NEW.student_id);
                SET present = (SELECT COUNT(*) FROM Attendance WHERE student_id = NEW.student_id AND status = 'Present');
                UPDATE Student_Performance SET attendance_rate = (present / total) * 100 WHERE student_id = NEW.student_id;
            END;
        """)

        # Example trigger: Prevent deletion of students with grades below threshold
        cursor.execute("""
            CREATE TRIGGER before_delete_student
            BEFORE DELETE ON Student
            FOR EACH ROW
            BEGIN
                IF (SELECT AVG(CAST(grade AS UNSIGNED)) FROM Grades WHERE student_id = OLD.student_id) < 50 THEN
                    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot delete students with average grade below 50';
                END IF;
            END;
        """)

        connection.commit()
        print("Tables and triggers created successfully.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()



class studentperformancetrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Performance Tracker")
        self.root.geometry("800x600")
        self.db_connection = connect_to_db()
        
        if self.db_connection is None:
            messagebox.showerror("Database Error", "Cannot connect to database")
            root.quit()
        
        self.show_login_page()

    def show_login_page(self):
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Login Interface
        tk.Label(self.root, text="Login", font=("Arial", 16)).pack(pady=20)
        
        tk.Label(self.root, text="Username:").pack(pady=5)
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack(pady=5)
        
        tk.Label(self.root, text="Password:").pack(pady=5)
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack(pady=5)
        
        login_button = tk.Button(self.root, text="Login", command=self.authenticate)
        login_button.pack(pady=20)

    def authenticate(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if username == "admin" and password == "admin123":
            self.show_admin_view()
        else:
            try:
                cursor = self.db_connection.cursor()
                cursor.execute("SELECT student_id, name FROM Student WHERE name = %s AND student_id = %s", (username, password))
                result = cursor.fetchone()
                
                if result:
                    self.student_id = result[0]  # Store student ID for student-specific queries
                    self.show_student_view()
                else:
                    messagebox.showerror("Login Failed", "Invalid username or password")
                    
                cursor.close()
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Database error: {err}")

    def show_admin_view(self):
        self.create_main_interface(is_admin=True)

    def show_student_view(self):
        self.create_main_interface(is_admin=False)

    def create_main_interface(self, is_admin):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        role_label = "Admin" if is_admin else "Student"
        tk.Label(self.root, text=f"{role_label} View", font=("Arial", 16)).pack(pady=20)

        # General buttons for both admin and students
        tk.Button(self.root, text="Load Courses", command=self.load_courses).pack(pady=5)
        tk.Button(self.root, text="Load Grades", command=self.load_grades).pack(pady=5)
        tk.Button(self.root, text="Load Attendance", command=self.load_attendance).pack(pady=5)

        # Admin-only buttons
        if is_admin:
            tk.Button(self.root, text="Update Attendance", command=self.update_attendance).pack(pady=5)
            tk.Button(self.root, text="Add Student", command=self.add_student).pack(pady=5)
            tk.Button(self.root, text="Load Students", command=self.load_students).pack(pady=5)
            tk.Button(self.root, text="Delete Student", command=self.delete_student).pack(pady=5)
            tk.Button(self.root, text="View Above Average Scores", command=self.load_above_average_scores).pack(pady=5)
            tk.Button(self.root, text="View Student Course Details", command=self.load_student_course_details).pack(pady=5)
            tk.Button(self.root, text="View Course Attendance Avg", command=self.load_course_attendance_avg).pack(pady=5)

        # Treeview for displaying data
        self.tree = ttk.Treeview(self.root)
        self.tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    def execute_query(self, query, params=()):
        cursor = self.db_connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        return result    

    def load_courses(self):
        query = "SELECT * FROM Course"
        columns = ("course_id", "course_name", "instructor", "schedule")
        self.load_data(query, columns)

    def load_grades(self):
        if hasattr(self, 'student_id'):  # Show only logged-in student's data if logged in as student
            query = "SELECT * FROM Grades WHERE student_id = %s"
            params = (self.student_id,)
            columns = ("grade_id", "student_id", "course_id", "grade", "grade_date")
            self.load_data(query, columns, params)
        else:
            query = "SELECT * FROM Grades"
            columns = ("grade_id", "student_id", "course_id", "grade", "grade_date")
            self.load_data(query, columns)

    def load_attendance(self):
        if hasattr(self, 'student_id'):  # Show only logged-in student's data if logged in as student
            query = "SELECT * FROM Attendance WHERE student_id = %s"
            params = (self.student_id,)
            columns = ("attendance_id", "student_id", "course_id", "attendance_date", "status")
            self.load_data(query, columns, params)
        else:
            query = "SELECT * FROM Attendance"
            columns = ("attendance_id", "student_id", "course_id", "attendance_date", "status")
            self.load_data(query, columns)

    def load_data(self, query, columns, params=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.tree["columns"] = columns
        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, anchor="center")
        
        try:
            cursor = self.db_connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
            cursor.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Database error: {err}")

    def update_attendance(self):
        update_window = tk.Toplevel(self.root)
        update_window.title("Update Attendance")

        tk.Label(update_window, text="Attendance ID").grid(row=0, column=0, padx=10, pady=5)
        attendance_id_entry = tk.Entry(update_window)
        attendance_id_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(update_window, text="Status (Present, Absent, Late)").grid(row=1, column=0, padx=10, pady=5)
        status_entry = tk.Entry(update_window)
        status_entry.grid(row=1, column=1, padx=10, pady=5)

        def submit_update():
            attendance_id = attendance_id_entry.get()
            status = status_entry.get()

            try:
                cursor = self.db_connection.cursor()
                cursor.execute("UPDATE Attendance SET status = %s WHERE attendance_id = %s", (status, attendance_id))
                self.db_connection.commit()
                cursor.close()
                messagebox.showinfo("Success", "Attendance updated successfully")
                update_window.destroy()
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Failed to update attendance: {err}")

        tk.Button(update_window, text="Update", command=submit_update).grid(row=2, columnspan=2, pady=10)

    def add_student(self):
        add_window = tk.Toplevel(self.root)
        add_window.title("Add Student")
        tk.Label(add_window, text="Name").grid(row=0, column=0, padx=10, pady=5)
        name_entry = tk.Entry(add_window)
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        tk.Label(add_window, text="Date of Birth (YYYY-MM-DD)").grid(row=1, column=0, padx=10, pady=5)
        dob_entry = tk.Entry(add_window)
        dob_entry.grid(row=1, column=1, padx=10, pady=5)
        tk.Label(add_window, text="Email").grid(row=2, column=0, padx=10, pady=5)
        email_entry = tk.Entry(add_window)
        email_entry.grid(row=2, column=1, padx=10, pady=5)
        tk.Label(add_window, text="Enrollment Year").grid(row=3, column=0, padx=10, pady=5)
        enrollment_entry = tk.Entry(add_window)
        enrollment_entry.grid(row=3, column=1, padx=10, pady=5)

        def submit():
            name = name_entry.get()
            dob = dob_entry.get()
            email = email_entry.get()
            enrollment_year = enrollment_entry.get()
            try:
                cursor = self.db_connection.cursor()
                cursor.execute(
                    "INSERT INTO Student (name, date_of_birth, email, enrollment_year) VALUES (%s, %s, %s, %s)",
                    (name, dob, email, enrollment_year)
                )
                self.db_connection.commit()
                cursor.close()
                messagebox.showinfo("Success", "Student added successfully")
                add_window.destroy()
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Failed to add student: {err}")

        tk.Button(add_window, text="Add", command=submit).grid(row=4, columnspan=2, pady=10)

    # Additional methods for load_students, delete_student, load_above_average_scores, load_student_course_details, load_course_attendance_avg would be implemented similarly, as per your data structure and requirements.

    def load_students(self):
        query = "SELECT * FROM Student"
        columns = ("student_id", "name", "date_of_birth", "email", "enrollment_year")
        self.load_data(query, columns)

    def delete_student(self):
        delete_window = tk.Toplevel(self.root)
        delete_window.title("Delete Student")
        tk.Label(delete_window, text="Enter Student ID to delete").pack(pady=10)
        student_id_entry = tk.Entry(delete_window)
        student_id_entry.pack(pady=5)

        def submit():
            student_id = student_id_entry.get()
            try:
                cursor = self.db_connection.cursor()
                cursor.execute("DELETE FROM Student WHERE student_id = %s", (student_id,))
                self.db_connection.commit()
                cursor.close()
                messagebox.showinfo("Success", "Student deleted successfully")
                delete_window.destroy()
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Failed to delete student: {err}")

        tk.Button(delete_window, text="Delete", command=submit).pack(pady=10)

    #nested query 
    def load_above_average_scores(self):
    # Create a popup window to ask for course_id
        course_id_window = tk.Toplevel(self.root)
        course_id_window.title("Select Course ID")
        tk.Label(course_id_window, text="Enter Course ID to find above-average scores").pack(pady=10)
        course_id_entry = tk.Entry(course_id_window)
        course_id_entry.pack(pady=5)

        def submit_course_id():
            course_id = course_id_entry.get()
            if not course_id.isdigit():
                messagebox.showerror("Invalid Input", "Please enter a valid Course ID")
                return
        
            # Define the query to get students with grades above average for the specified course
            query = '''
            SELECT s.student_id, s.name, g.grade
            FROM Grades g
            JOIN Student s ON g.student_id = s.student_id
            WHERE g.course_id = %s AND 
                CAST(g.grade AS UNSIGNED) > (
                    SELECT AVG(CAST(grade AS UNSIGNED)) 
                    FROM Grades 
                    WHERE course_id = %s
                  );
            '''
            columns = ("student_id", "name", "grade")
            self.load_data(query, columns, (course_id, course_id))
            course_id_window.destroy()

        tk.Button(course_id_window, text="Submit", command=submit_course_id).pack(pady=10)


    # 2. Join Query: Fetch student and course details
    def load_student_course_details(self):
        query = '''
        SELECT Student.student_id, Student.name, Course.course_name
        FROM Student
        JOIN Grades ON Student.student_id = Grades.student_id
        JOIN Course ON Grades.course_id = Course.course_id;
        '''
        columns = ("student_id", "name", "course_name")
        self.load_data(query, columns)

    # 3. Aggregated Query: Get average attendance status per course
    def load_course_attendance_avg(self):
        query = '''
        SELECT course_id, AVG(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) * 100 AS attendance_rate
        FROM Attendance
        GROUP BY course_id;
        '''
        columns = ("course_id", "attendance_rate")
        self.load_data(query, columns)


# Main application
if __name__ == "__main__":
    setup_database()
    root = tk.Tk()
    app = studentperformancetrackerApp(root)
    root.mainloop()