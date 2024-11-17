import xmlrpc.client
import streamlit as st
import uuid
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from streamlit_router import StreamlitRouter

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None

with open('config.yml') as file:
    config = yaml.load(file, Loader=SafeLoader)

names = ["Soorya Sivaramakrishnan", "Tanish Patil", "Tushar Raja"]
usernames = ["2022300122", "2022300128", "2022300130"]

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login(location="main", key="Login")

if st.session_state["authentication_status"] == False:
    st.error("Invalid username or password")
elif st.session_state["authentication_status"] == None:
    st.warning("Please enter your credentials")
else:
    # Generate a unique session code for each new webpage (client session)
    def index(router):
        st.write("Welcome to Exam Management system")

    if "session_code" not in st.session_state:
        st.session_state.session_code = str(uuid.uuid4())
    session_code = st.session_state.session_code

    # Connect to the server (leader-aware connection)
    def connect_to_server():
        leader_url = "http://localhost:5000/"
        try:
            leader_server = xmlrpc.client.ServerProxy(leader_url)
            leader = leader_server.get_leader()
            st.session_state.server_url = f"http://localhost:{5000 + leader}/"  # Simulating leader-based port adjustment
            return xmlrpc.client.ServerProxy(st.session_state.server_url)
        except Exception as e:
            st.error(f"Failed to connect to leader server: {e}")
            return None

    server = connect_to_server()

    # Initialize the client session with the server using the session code
    if server:
        try:
            client_id = server.initialize_client(session_code)
            st.write(f"Session successfully initialized with ID: {client_id}")
        except Exception as e:
            st.error(f"Failed to initialize client session: {e}")

    # Streamlit interface
    st.title("Welcome to the Exam Registration System")
    st.sidebar.title(f"Welcome {st.session_state['name']}")
    authenticator.logout('Logout', 'sidebar')

    # Exam schedule section
    st.header("Exam Schedule")
    if st.button("View Schedule"):
        try:
            exams = server.view_schedule(session_code)
            if exams:
                st.write("Exam Schedule:")
                st.table(exams)
            else:
                st.write("No exams scheduled.")
        except Exception as e:
            st.error(f"Failed to retrieve exam schedule: {e}")

    # Exam registration section
    st.header("Register for an Exam")
    exam_id = st.text_input("Enter Exam ID")
    if st.button("Register"):
        try:
            response = server.register_exam(session_code, exam_id)
            st.success(response)
        except Exception as e:
            st.error(f"Failed to register for exam: {e}")

    # Display the unique session code (for debugging and identification)
    st.write(f"Your unique session code is: {session_code}")
