# --- Imports and Setup ---
import streamlit as st
import time
import re
import json
import pandas as pd
import pyperclip
import csv
from datetime import datetime
from supabase import create_client, Client

print("Supbase imported successfully")
# Initialize Supabase client
supabase_url = st.secrets["supabase_url"]
supabase_key = st.secrets["supabase_key"]
supabase: Client = create_client(supabase_url, supabase_key)
print("Supabase client created successfully")


print("Initializing Streamlit app...")

# --- Load Data ---
with open("all_prompts.json", "r", encoding="utf-8") as f:
    parsed_templates = json.load(f)
    prompt_df = pd.DataFrame(parsed_templates)
    prompt_df = prompt_df[
        prompt_df["complexity"] == "Medium"
    ]  # filter out low complexity prompts


# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Nonprofit Prompt Assistant",
    page_icon="your_logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)
# --- Sidebar Styling and Logo ---

with st.sidebar:

    st.html(
        """
    <style>
    [data-testid="stSidebarContent"] {
        color: white;
        background-color: #0057b8;
    }
    </style>
    """
    )

    # display logo image in sidebar
    st.sidebar.image("your_logo.png", width="stretch")


# --- Color Styling ---
st.markdown(
    """
    <style>
        .main {background-color: #C1C6C8;}
        h1, h2, h3, h4 {color: #0057b8;}
        .stButton>button {background-color: #78BE20; color: white;}
        .stTextInput>div>input {border-color: #ED8B00;}
    </style>
""",
    unsafe_allow_html=True,
)


# --- Highlight Function ---
def highlight_variables(prompt_text, inputs):
    highlighted = prompt_text
    for var in inputs:
        value = inputs[var] if inputs[var] else f"[{var}]"
        styled_value = f"<span style='background-color:#ED8B00; color:white; padding:2px 4px; border-radius:4px;'>{value}</span>"
        highlighted = highlighted.replace(f"[{var}]", styled_value)
    return highlighted


# -- Landing Page ---
if "page" not in st.session_state:
    st.session_state.page = "landing"

if st.session_state.page == "landing":
    st.title("Welcome to the Nonprofit Prompt Assistant")
    st.markdown(
        """
        This prototype app helps nonprofit professionals streamline their work using AI-generated prompts.
        
        ✅ Choose a task category  

        The categories are designed specifically for nonprofit operations, fundraising, and program management.

        ✅ Fill in standard information  

        This information will be used to customize the prompts to your organization's context.

        ✅ Get a customized prompt instantly  
        You can copy the prompt to your clipboard and use it immediately.
        
        At the end, we'd love your feedback and email so we can keep improving!
    """
    )
    if st.button("Start Using the Assistant"):
        st.session_state.page = "main"
        st.rerun()

elif st.session_state.page == "main":
    # --- Main Application Logic ---
    # Initialize session state
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = None
    if "selected_template" not in st.session_state:
        st.session_state.selected_template = None
    if "selected_topic" not in st.session_state:
        st.session_state.selected_topic = None
    if "inputs" not in st.session_state:
        st.session_state.inputs = {}
    if "organization_name" not in st.session_state:
        st.session_state.organization_name = ""

    st.title("Nonprofit Prompt Assistant")

    # Step 1: Organization Name
    org_name = st.text_input("Enter your Organization Name", key="user_org_name")
    st.session_state.organization_name = org_name

    # Step 2: Category Selection
    st.subheader("Choose task where you need help with")
    categories = list(prompt_df["category"].unique())
    selected_category = st.selectbox("Select a Category", categories)
    st.session_state.selected_category = selected_category

    # Step 3: Template Selection
    template_choices = list(
        prompt_df[prompt_df["category"] == selected_category]["template_type"].unique()
    )
    selected_template = st.selectbox(
        "Select a task template", template_choices
    )  # needs better name
    st.session_state.selected_template = selected_template

    # Step 4: Task Choice Selection
    filtered_df = prompt_df[
        (prompt_df["category"] == selected_category)
        & (prompt_df["template_type"] == selected_template)
    ]
    task_choices = filtered_df["topic"].tolist()
    selected_topic = st.selectbox("Select a task", task_choices)
    st.session_state.selected_topic = selected_topic

    # Step 5: Fill-in-the-blank fields
    chosen_prompt = filtered_df[filtered_df["topic"] == selected_topic]
    prompt_text = chosen_prompt["prompt_text"].values[0]
    variables = chosen_prompt["variables"].values[0]

    # Side-by-Side Layout
    st.subheader("Customize Your Prompt")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Fill in the blanks")
        for var in variables:
            helper_text = (
                f"Enter your {var.replace('_', ' ').lower()} here."  # Placeholder
            )
            user_input = st.text_input(
                var.replace("_", " ").title(), help=helper_text, key=var
            )
            st.session_state.inputs[var] = user_input

    with col2:
        final_prompt = prompt_text
        for var, value in st.session_state.inputs.items():
            final_prompt = final_prompt.replace(f"[{var}]", value)
        st.markdown("### Live Prompt Preview")
        st.markdown(
            highlight_variables(prompt_text, st.session_state.inputs),
            unsafe_allow_html=True,
        )

    if st.button("Copy to Clipboard"):
        pyperclip.copy(final_prompt)
        st.success("Prompt copied to clipboard!")

    # Feedback Section
    st.subheader("We'd love your feedback")
    email = st.text_input("Your Email", key="email")
    helpful = st.radio("Did this prompt help you?", ["Yes", "No"])
    feedback = st.text_area("How did it help or not help you?")

    if st.button("Submit"):
        st.success("Your response has been recorded.")

        response = {
            "timestamp": datetime.now().isoformat(),
            "organization": org_name,
            "email": email,
            "category": selected_category,
            "template": selected_template,
            "topic": selected_topic,
            "prompt": prompt_text,
            "final_prompt": final_prompt,
            "helpful": helpful,
            "feedback": feedback,
        }
        try:
            supabase.table("responses").insert(response).execute()
            st.success("Your supabase response has been saved successfully!")
        except Exception as e:
            st.error(f"Error saving response in supabase: {e}")

    if st.button("Reset and Start Over"):
        for key in [
            "start_time",
            "selected_category",
            "selected_template",
            "selected_topic",
            "inputs",
        ]:
            st.session_state.pop(key, None)
        st.session_state.page = "main"
        st.rerun()
