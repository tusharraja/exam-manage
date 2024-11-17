import streamlit as st
import random
import time
from datetime import datetime, timedelta
import threading
import queue
from collections import defaultdict

# Simulating distributed system components
class Node:
    def __init__(self, node_id):
        self.id = node_id
        self.lamport_clock = 0
        self.is_coordinator = False
        self.load = 0
        self.exam_data = {}
        self.replica_data = {}
        self.lock = threading.Lock()

class DistributedExamSystem:
    def __init__(self):
        # Initialize nodes only if they don't already exist in session state
        if 'nodes' not in st.session_state:
            st.session_state.nodes = [Node(i) for i in range(3)]  # Creating 3 nodes
        self.nodes = st.session_state.nodes
        self.coordinator = None
        self.message_queue = queue.Queue()
        self.queue_lock = threading.Lock()  # Control access to the message queue
        self.elect_coordinator()
        
    def lamport_timestamp(self, sender_node, receiver_node):
        """Implementation of Lamport's logical clock"""
        with sender_node.lock:
            sender_node.lamport_clock += 1
            send_time = sender_node.lamport_clock
            
        with receiver_node.lock:
            receiver_node.lamport_clock = max(receiver_node.lamport_clock, send_time) + 1
            
    def elect_coordinator(self):
        """Implementation of Bully Algorithm"""
        highest_id = max(node.id for node in self.nodes)
        for node in self.nodes:
            node.is_coordinator = (node.id == highest_id)
            if node.is_coordinator:
                self.coordinator = node
                
    def replicate_data(self, data, source_node):
        """Data replication across nodes"""
        with source_node.lock:  # Global lock for data replication
            for node in self.nodes:
                if node != source_node:
                    node.replica_data.update(data)
                    self.lamport_timestamp(source_node, node)
                
    def load_balance(self):
        """Simple load balancing implementation"""
        loads = [node.load for node in self.nodes]
        return self.nodes[loads.index(min(loads))]
        
    def acquire_lock(self, resource_id, node):
        """Mutual exclusion implementation"""
        with self.queue_lock:
            while resource_id in [msg[1] for msg in self.message_queue.queue]:
                time.sleep(0.1)
            self.message_queue.put((node.id, resource_id))
                
    def release_lock(self, resource_id, node):
        """Release mutual exclusion lock"""
        with self.queue_lock:
            try:
                self.message_queue.queue.remove((node.id, resource_id))
            except ValueError:
                pass

class ExamDatabase:
    def __init__(self):
        # Initialize with default data structures if they don't exist in session state
        if 'users' not in st.session_state:
            st.session_state.users = {}
        if 'exams' not in st.session_state:
            st.session_state.exams = {}
        if 'responses' not in st.session_state:
            st.session_state.responses = {}
        if 'slots' not in st.session_state:
            st.session_state.slots = defaultdict(list)
        
    def add_user(self, username, password, role):
        st.session_state.users[username] = {"password": password, "role": role}
        
    def add_exam(self, exam_id, questions, duration):
        st.session_state.exams[exam_id] = {
            "questions": questions,
            "duration": duration,
            "active": True
        }
        
    def add_response(self, username, exam_id, responses):
        st.session_state.responses[(username, exam_id)] = responses
        
    def add_slot(self, exam_id, slot_time):
        if slot_time not in st.session_state.slots[exam_id]:
            st.session_state.slots[exam_id].append(slot_time)
        
    def get_available_exams(self):
        return {k: v for k, v in st.session_state.exams.items() if v.get('active', True)}

class ExamSystemUI:
    def __init__(self):
        self.db = ExamDatabase()
        self.distributed_system = DistributedExamSystem()
        
    def login_page(self):
        st.title("Exam System Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["admin", "student"])
        
        if st.button("Login"):
            if username not in st.session_state.users:
                self.db.add_user(username, password, role)
                st.success("Account created successfully!")
            elif st.session_state.users[username]["password"] == password:
                st.session_state.user = username
                st.session_state.role = role
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials!")
                
    def admin_dashboard(self):
        st.title("Admin Dashboard")
        
        # Create Exam Section
        st.header("Create Exam")
        exam_id = st.text_input("Exam ID")
        num_questions = st.number_input("Number of Questions", min_value=1, value=5)
        
        if exam_id and num_questions > 0:
            questions = []
            for i in range(num_questions):
                st.subheader(f"Question {i+1}")
                question = st.text_input(f"Question {i+1} text", key=f"q{i}")
                options = []
                for j in range(4):
                    option = st.text_input(f"Option {j+1}", key=f"q{i}o{j}")
                    options.append(option)
                if all(options):  # Only show correct answer selection if all options are filled
                    correct_answer = st.selectbox(f"Correct Answer for Q{i+1}", options, key=f"ca{i}")
                    questions.append({
                        "question": question,
                        "options": options,
                        "correct_answer": correct_answer
                    })
            
            duration = st.number_input("Duration (minutes)", min_value=10, value=60)
            
            if st.button("Create Exam"):
                if len(questions) == num_questions:
                    node = self.distributed_system.load_balance()
                    self.distributed_system.acquire_lock(exam_id, node)
                    
                    try:
                        if exam_id not in st.session_state.exams:
                            self.db.add_exam(exam_id, questions, duration)
                            # Replicate exam data
                            self.distributed_system.replicate_data({exam_id: questions}, node)
                            st.success(f"Exam '{exam_id}' created successfully!")
                            st.rerun()
                        else:
                            st.error("An exam with this ID already exists!")
                    finally:
                        self.distributed_system.release_lock(exam_id, node)
                else:
                    st.error("Please complete all questions and options before creating the exam!")
        
        # Show Created Exams
        st.header("Created Exams")
        if st.session_state.exams:
            for exam_id, exam in st.session_state.exams.items():
                st.subheader(f"Exam: {exam_id}")
                st.write(f"Duration: {exam['duration']} minutes")
                st.write(f"Number of questions: {len(exam['questions'])}")
                
                # Add button to toggle exam visibility
                active = st.checkbox("Active", value=exam.get('active', True), key=f"active_{exam_id}")
                if active != exam.get('active', True):
                    st.session_state.exams[exam_id]['active'] = active
                    st.rerun()
        else:
            st.info("No exams have been created yet.")
                
        # Generate Reports Section
        if st.session_state.exams:
            st.header("Generate Reports")
            exam_select = st.selectbox("Select Exam", list(st.session_state.exams.keys()))
            if st.button("Generate Report"):
                report = self.generate_report(exam_select)
                if report:
                    st.write("Exam Results:")
                    for username, data in report.items():
                        st.write(f"Student: {username}")
                        st.write(f"Score: {data['score']:.2f}%")
                        st.write(f"Correct Answers: {data['correct_answers']}/{data['total_questions']}")
                        st.write("---")
                else:
                    st.info("No submissions for this exam yet.")
            
    def student_dashboard(self):
        st.title("Student Dashboard")
        
        # View Available Exams
        st.header("Available Exams")
        available_exams = self.db.get_available_exams()
        
        if available_exams:
            for exam_id, exam in available_exams.items():
                st.subheader(f"Exam: {exam_id}")
                st.write(f"Duration: {exam['duration']} minutes")
                st.write(f"Number of questions: {len(exam['questions'])}")
                
                # Book Slot
                available_slots = st.session_state.slots.get(exam_id, [])
                if not available_slots:
                    # Create default slots for next 7 days
                    current_date = datetime.now()
                    for i in range(7):
                        slot_time = (current_date.replace(hour=9, minute=0, second=0) + 
                                   timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
                        self.db.add_slot(exam_id, slot_time)
                    available_slots = st.session_state.slots[exam_id]
                
                selected_slot = st.selectbox(
                    f"Available Slots for {exam_id}",
                    available_slots,
                    key=f"slot_{exam_id}"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"Book Slot for {exam_id}", key=f"book_{exam_id}"):
                        st.session_state.user_slot = (exam_id, selected_slot)
                        st.success(f"Slot booked for {exam_id} on {selected_slot}")
                
                with col2:
                    if st.button(f"Take Exam {exam_id}", key=f"take_{exam_id}"):
                        st.session_state.current_exam = exam_id
                        st.session_state.current_question = 0
                        st.session_state.responses = {}
                        st.experimental_rerun()
        else:
            st.info("No exams available.")

    def generate_report(self, exam_id):
        exam = st.session_state.exams.get(exam_id)
        if not exam:
            return None
        total_questions = len(exam["questions"])
        report = {}
        for (username, ex_id), responses in st.session_state.responses.items():
            if ex_id == exam_id:
                correct_answers = sum(
                    1 for i, q in enumerate(exam["questions"])
                    if responses.get(i) == q["correct_answer"]
                )
                score = (correct_answers / total_questions) * 100
                report[username] = {
                    "score": score,
                    "correct_answers": correct_answers,
                    "total_questions": total_questions
                }
        return report

    def exam_page(self):
        exam_id = st.session_state.get("current_exam")
        question_idx = st.session_state.get("current_question", 0)
        
        if exam_id is None:
            st.write("No exam selected.")
            return
        
        exam = st.session_state.exams.get(exam_id)
        if exam and question_idx < len(exam["questions"]):
            question = exam["questions"][question_idx]
            st.write(f"Question {question_idx + 1}: {question['question']}")
            response = st.radio(
                "Select an answer:",
                question["options"],
                key=f"response_{question_idx}"
            )
            
            if st.button("Next"):
                st.session_state.responses[question_idx] = response
                st.session_state.current_question += 1
                if st.session_state.current_question >= len(exam["questions"]):
                    self.db.add_response(st.session_state.user, exam_id, st.session_state.responses)
                    st.success("Exam submitted!")
                    del st.session_state.current_exam
                    del st.session_state.current_question
                    del st.session_state.responses
                st.experimental_rerun()

def main():
    ui = ExamSystemUI()
    
    if "user" not in st.session_state:
        ui.login_page()
    else:
        role = st.session_state.role
        if role == "admin":
            ui.admin_dashboard()
        elif role == "student":
            if "current_exam" in st.session_state:
                ui.exam_page()
            else:
                ui.student_dashboard()

if __name__ == "__main__":
    main()
