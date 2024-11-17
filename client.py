import xmlrpc.client
import streamlit as st
import uuid
import time

# Generate a unique session code for each new webpage (client session)
if "session_code" not in st.session_state:
    st.session_state.session_code = str(uuid.uuid4())
session_code = st.session_state.session_code

# Connect to the server (handles leader retrieval for dynamic coordination)
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
    except Exception as e:
        st.error(f"Failed to initialize client session: {e}")

# Streamlit interface
st.title("Welcome to the Examination System")
st.sidebar.title(f"Welcome {st.session_state.get('name', 'User')}")

st.header("Open Exams")
if st.button("DSGT-ISE 1"):
    exam_duration = 300  # Set exam duration in seconds (e.g., 5 minutes)
    end_time = time.time() + exam_duration
    ans = "None"
    val = 1
    try:
        while time.time() < end_time:
            exams = server.dsgt(val, st.session_state.get("name", "Unknown"), ans)
            if exams != "Exit":
                st.write(exams[0][0])
                ans = st.text_input("Enter Answer", key=f"answer_{int(time.time())}")
                val += 1
            elif exams == "Exit":
                st.write("Exam Finished")
                break
            else:
                st.write(f"You have already given this exam. Your score is {exams}")

            # Update the remaining time
            remaining_time = int(end_time - time.time())
            st.write(f"Time remaining: {remaining_time} seconds")

            if remaining_time <= 0:
                st.write("Time is up! Exam has ended.")
                break

            # Add a short sleep to prevent excessive CPU usage
            time.sleep(1)

    except Exception as e:
        st.error(f"Failed to retrieve exam schedule: {e}")
