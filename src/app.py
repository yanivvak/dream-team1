import streamlit as st
import sys
import asyncio
import logging
import os
import json
from datetime import datetime 
from dotenv import load_dotenv
load_dotenv()
from magentic_one_helper import MagenticOneHelper

#Enable asyncio for Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Initialize a global cancellation event
cancel_event = asyncio.Event()

# Initialize session state for instructions
if 'instructions' not in st.session_state:
    st.session_state['instructions'] = ""

if 'running' not in st.session_state:
    st.session_state['running'] = False

if "final_answer" not in st.session_state:
    st.session_state["final_answer"] = None

if "run_mode_locally" not in st.session_state:
    st.session_state["run_mode_locally"] = True


if 'max_rounds' not in st.session_state:
    st.session_state.max_rounds = 30
if 'max_time' not in st.session_state:
    st.session_state.max_time = 25
if 'max_stalls_before_replan' not in st.session_state:
    st.session_state.max_stalls_before_replan = 5
if 'return_final_answer' not in st.session_state:
    st.session_state.return_final_answer = True
if 'start_page' not in st.session_state:
    st.session_state.start_page = "https://www.bing.com"


st.title("Dream Team powered by Magentic 1")

image_path = "contoso.png"  
  
# Display the image in the sidebar  
with st.sidebar:
    st.image(image_path, use_container_width=True) 

    with st.container(border=True):
        st.caption("Settings:")
        st.session_state.max_rounds = st.number_input("Max Rounds", min_value=1, value=50)
        st.session_state.max_time = st.number_input("Max Time (Minutes)", min_value=1, value=10)
        st.session_state.max_stalls_before_replan = st.number_input("Max Stalls Before Replan", min_value=1, max_value=10, value=5)
        st.session_state.return_final_answer = st.checkbox("Return Final Answer", value=True)
        st.session_state.start_page = st.text_input("Start Page URL", value="https://www.bing.com")
        

        

run_button_text = "Run Agents"
if not st.session_state['running']:
      
    st.write("Our AI agents are ready to assist you. Our line up:")
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])

    with c1:
        with st.container(border=True):
            st.write("🎻") 
            st.caption("Orchestrator")
    with c2:
        with st.container(border=True):
            st.write("🏄‍♂️")
            st.caption("WebSurfer")
    with c3:
        with st.container(border=True):
            st.write("👨‍💻")
            st.caption("Coder")
    with c4:
        with st.container(border=True):
            st.write("📂")
            st.caption("FileSurfer")
    with c5:
        with st.container(border=True):
            st.write("💻")
            st.caption("Executor")

        

    # Define predefined values
    predefined_values = [
        "Find me a French restaurant in Dubai with 2 Michelin stars?",
        "When and where is the next game of Arsenal, print a link for purchase",
        "Generate a python script to print Fibonacci series below 1000",
    ]

    # Add an option for custom input
    custom_option = "Write your own query"

    # Use selectbox for predefined values and custom option
    selected_option = st.selectbox("Select your instructions:", options=predefined_values + [custom_option])

    # If custom option is selected, show text input for custom instructions
    if selected_option == custom_option:
        instructions = st.text_input("Enter your custom instructions:")
    else:
        instructions = selected_option

    # Update session state with instructions
    st.session_state['instructions'] = instructions
    
    run_mode_locally = st.toggle("Run Locally", value=False)
    if run_mode_locally:
        st.session_state["run_mode_locally"] = True
        st.caption("Run Locally: Run the workflow in a Docker container on your local machine.")
    else:
        st.caption("Run in Azure: Run the workflow in a ACA Dynamic Sessions on Azure.")
        # check if the Azure infra is setup
        _pool_endpoint=os.getenv("POOL_MANAGEMENT_ENDPOINT")
        if not _pool_endpoint:
            st.error("You need to setup the Azure infra first. Try `azd up` in your project.")
            # st.session_state["run_mode_locally"] = True
            # st.rerun()
        st.session_state["run_mode_locally"] = False
else:
    run_button_text = "Cancel Run"



if st.button(run_button_text, type="primary"):
    if not st.session_state['running']:
        st.session_state['instructions'] = instructions
        st.session_state['running'] = True
        st.session_state['final_answer'] = None
        cancel_event.clear()  # Clear the cancellation event
        st.rerun()
    else:
        st.session_state['running'] = False
        st.session_state['instructions'] = ""
        st.session_state['final_answer'] = None
        st.session_state["run_mode_locally"] = True
        cancel_event.set()  # Set the cancellation event
        st.rerun()

def display_log_message(log_entry):     
    # _log_entry_json  = json.loads(log_entry)
    _log_entry_json  = log_entry

    _type = _log_entry_json.get("type", None)
    _timestamp = _log_entry_json.get("timestamp", None)
    _timestamp = datetime.fromisoformat(_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    # _src = _log_entry_json["source"]
    agent_icon = "🚫"

    if _type == "OrchestrationEvent" or _type == "WebSurferEvent":
        if str(_log_entry_json["source"]).startswith("Orchestrator"):
            agent_icon = "🎻"
        elif _log_entry_json["source"] == "WebSurfer":
            agent_icon = "🏄‍♂️"
        elif _log_entry_json["source"] == "Coder":
            agent_icon = "👨‍💻"
        elif _log_entry_json["source"] == "FileSurfer":
            agent_icon = "📂"
        elif _log_entry_json["source"] == "Executor":
            agent_icon = "💻"
        elif _log_entry_json["source"] == "UserProxy":
            agent_icon = "👤"
        else:
            agent_icon = "🤖"
        with st.expander(f"{agent_icon} {_log_entry_json['source']} @ {_timestamp}", expanded=True):
            st.write(_log_entry_json["message"])
    elif _type == "LLMCallEvent":
        st.caption(f'{_timestamp} LLM Call [prompt_tokens: {_log_entry_json["prompt_tokens"]}, completion_tokens: {_log_entry_json["completion_tokens"]}]')
    else:
        st.caption("🤔 Agents mumbling...")


async def main(task, logs_dir="./logs"):
    
    # create folder for logs if not exists
    if not os.path.exists(logs_dir):    
        os.makedirs(logs_dir)

    # Initialize MagenticOne
    magnetic_one = MagenticOneHelper(logs_dir=logs_dir, run_locally=st.session_state["run_mode_locally"])
    magnetic_one.max_rounds = st.session_state.max_rounds
    magnetic_one.max_time = st.session_state.max_time * 60
    magnetic_one.max_stalls_before_replan = st.session_state.max_stalls_before_replan
    magnetic_one.return_final_answer = st.session_state.return_final_answer
    magnetic_one.start_page = st.session_state.start_page

    await magnetic_one.initialize()
    print("MagenticOne initialized.")

    # Create task and log streaming tasks
    task_future = asyncio.create_task(magnetic_one.run_task(task))
    final_answer = None

    with st.container(border=True):    
        # Stream and process logs
        async for log_entry in magnetic_one.stream_logs():
            # print(json.dumps(log_entry, indent=2))
            # st.write(json.dumps(log_entry, indent=2))
            display_log_message(log_entry=log_entry)

    # Wait for task to complete
    await task_future

    # Get the final answer
    final_answer = magnetic_one.get_final_answer()

    if final_answer is not None:
        print(f"Final answer: {final_answer}")
        st.session_state["final_answer"] = final_answer
    else:
        print("No final answer found in logs.")
        st.session_state["final_answer"] = None
        st.warning("No final answer found in logs.")

if st.session_state['running']:
    assert st.session_state['instructions'] != "", "Instructions can't be empty."

    with st.spinner("Dream Team is running..."):
        # asyncio.run(main("generate code and calculate with python 132*82"))
        # asyncio.run(main("generate code for 'Hello World' in Python"))
        asyncio.run(main(st.session_state['instructions']))

    final_answer = st.session_state["final_answer"]
    if final_answer:
        st.success("Task completed successfully.")
        st.write("## Final answer:")
        st.write(final_answer)
    else:
        st.error("Task failed.")
        st.write("Final answer not found.")
