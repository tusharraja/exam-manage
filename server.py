# Import necessary modules
from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import mysql.connector
import threading
import time
from datetime import datetime
import uuid

# Configure MySQL connection
db_config = {
    'host': 'localhost',  # Change to your MySQL host if necessary
    'user': 'root',
    'password': '@Tomic123',
    'database': 'soorya'
}

# Dictionary to store active sessions and their respective request timestamps
sessions = {}
mutex_lock = threading.Lock()
deferred_requests = []

# Critical section request management based on Ricart-Agrawala algorithm
class MutexManager:
    def __init__(self):
        self.current_request = None  # Stores the current session holding the critical section
        self.request_queue = []      # Queue of deferred requests (session codes)

    def request_entry(self, session_code, timestamp):
        with mutex_lock:
            # If no one is holding the critical section, grant access
            if not self.current_request:
                self.current_request = session_code
                print(f"{session_code} granted access to register for exam.")
                return True
            
            # If someone else holds the critical section, compare timestamps
            current_time = datetime.now().timestamp()
            if timestamp < current_time:
                # Queue this request to defer it
                self.request_queue.append((session_code, timestamp))
                print(f"{session_code} request deferred. Queue length: {len(self.request_queue)}")
                return False
            else:
                self.request_queue.append((session_code, timestamp))
                return False

    def release_entry(self, session_code):
        with mutex_lock:
            if self.current_request == session_code:
                print(f"{session_code} has released the critical section.")
                self.current_request = None

                # Grant access to the next request in the queue if any
                if self.request_queue:
                    next_request = min(self.request_queue, key=lambda x: x[1])  # Get the earliest request by timestamp
                    self.request_queue.remove(next_request)
                    self.current_request = next_request[0]
                    print(f"{next_request[0]} granted access to register for exam after release.")
                    return next_request[0]  # Grant access to the next client
            return None

mutex_manager = MutexManager()

# Define server functions
def initialize_client(session_code):
    """Initialize a new client session with a unique session code if it doesn't already exist."""
    if session_code not in sessions:
        sessions[session_code] = {
            'thread_name': f"Client-{session_code}"
        }
        print(f"Assigned new session with ID: {session_code}.")
    return session_code

def view_schedule(session_code):
    """Fetches the exam schedule from the database for a specific session."""
    print(f"Client {session_code} requested to view schedule.")
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id, Name, Marks, Student_registered, Exam_date, Start_time, Duration FROM scheduled")
    exams = cursor.fetchall()
    cursor.close()
    connection.close()
    return exams

def register_exam(session_code, exam_id):
    """Registers a user for an exam by incrementing the registered students count, using Ricart-Agrawala mutual exclusion."""
    timestamp = datetime.now().timestamp()
    can_access = mutex_manager.request_entry(session_code, timestamp)
    
    if not can_access:
        return "Request deferred; waiting for access to register."

    # Perform the registration in the critical section
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        statement = f'UPDATE scheduled SET Student_registered = Student_registered + 1 WHERE Name = "{exam_id}";'
        cursor.execute(statement)
        connection.commit()
        rows_affected = cursor.rowcount
        cursor.close()
        connection.close()
        
        # Check if registration was successful
        if rows_affected == 0:
            return "Exam ID not found"
        return "Registered successfully"
    finally:
        # Release the critical section
        mutex_manager.release_entry(session_code)

# Extend SimpleXMLRPCServer with threading capabilities
class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

# Set up the multithreaded XML-RPC server
server = ThreadedXMLRPCServer(("0.0.0.0", 5000), allow_none=True)
print("Multithreaded server with replication and load balancing running on port 5000...")

# Register functions
server.register_function(initialize_client, "initialize_client")
server.register_function(view_schedule, "view_schedule")
server.register_function(register_exam, "register_exam")

# Run the server
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nServer is shutting down.")
