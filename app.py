# --- Imports and Setup ---
import streamlit as st
import time
import re
import json
import pandas as pd
import pyperclip
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
# landing_response = {}

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
        .stNumberInput input {border-color: #ED8B00;}
        .stSelectbox div[data-baseweb="select"] {border-color: #ED8B00;}
    </style>
""",
    unsafe_allow_html=True,
)

# --- Helpers ---
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


# --- Highlight Function ---
def highlight_variables(prompt_text, inputs):
    highlighted = prompt_text
    for var in inputs:
        value = inputs[var] if inputs[var] else f"[{var}]"
        styled_value = f"<span style='background-color:#ED8B00; color:white; padding:2px 4px; border-radius:4px;'>{value}</span>"
        highlighted = highlighted.replace(f"[{var}]", styled_value)
    return highlighted


# --- Session State Init ---
if "page" not in st.session_state:
    st.session_state.page = "landing"
if "contact" not in st.session_state:
    st.session_state.contact = {"email": "", "org": "", "role": ""}
if "start_time" not in st.session_state:
    st.session_state.start_time = None
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
if "difficulty_more" not in st.session_state:
    st.session_state.difficulty_more = ""

# -- Landing Page (New Version) --
if st.session_state.page == "landing":
    st.title("Welcome to the Nonprofit Prompt Assistant")

    st.markdown(
        """
        This app helps nonprofit professionals **choose the right AI prompt** and **fill it out quickly** so you can get quality drafts, plans, emails, and analyses—faster.

        ### What this app does
        - **Browse nonprofit‑specific task categories** (fundraising, programs, ops, comms, etc.)
        - **Fill simple blanks** about your context; we build a tailored prompt for you
        - **Copy your custom prompt** and use it directly in your AI tool of choice

        ### Why we ask for contact info
        We collect **email, organization name, and your role** to:
        - Understand who we’re serving and improve coverage of nonprofit roles
        - Reach out (rarely) to invite you to pilots or ask for feedback (you can opt out any time)
        - Prevent duplicate submissions and improve data quality
        """
    )

    with st.form("contact_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@nonprofit.org")
        org = st.text_input(
            "Organization Name", placeholder="e.g., Helping Hands Foundation"
        )
        role = st.text_input("Your Role", placeholder="e.g., Development Manager")
        submit = st.form_submit_button("Continue")

    if submit:
        errors = []
        if not org.strip():
            errors.append("Organization name is required.")
        if not role.strip():
            errors.append("Role is required.")
        if not email.strip() or not is_valid_email(email.strip()):
            errors.append("Please enter a valid email address.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            st.session_state.contact = {
                "email": email.strip(),
                "org": org.strip(),
                "role": role.strip(),
            }
            st.session_state.organization_name = org.strip()
            st.session_state.start_time = time.time()

            landing_response = {
                # "timestamp": datetime.now().isoformat(),
                "email": st.session_state.contact["email"],
                "organization": st.session_state.contact["org"],
                "role": st.session_state.contact["role"],
            }
            # Optionally record contact entry (safe to ignore failure)
            try:
                # landing_response = {
                #     # "timestamp": datetime.now().isoformat(),
                #     "email": st.session_state.contact["email"],
                #     "organization": st.session_state.contact["org"],
                #     "role": st.session_state.contact["role"],
                # }
                supabase.table("contacts").insert(landing_response).execute()
            except Exception as e:
                st.info(f"(Optional) Could not save contact record: {e}")

            st.session_state.page = "main"
            st.rerun()

# --- Main Application ---
elif st.session_state.page == "main":
    st.title("Nonprofit Prompt Assistant")

    # Step 1: Category Selection
    st.subheader("Choose the task where you need help")
    categories = list(
        prompt_df["openai_topic"].unique()
    )  # change this line to openai inferred categories later
    selected_category = st.selectbox("Select a Category", categories)
    st.session_state.selected_category = selected_category

    # Step 2: Template Selection
    template_choices = list(
        prompt_df[prompt_df["openai_topic"] == selected_category][
            "template_type"
        ].unique()
    )  # changed category to openai_topic
    selected_template = st.selectbox("Select a task template", template_choices)
    st.session_state.selected_template = selected_template

    # Step 3: Task Choice Selection
    filtered_df = prompt_df[
        (
            prompt_df["openai_topic"] == selected_category
        )  # changed category to openai_topic
        & (prompt_df["template_type"] == selected_template)
    ]
    task_choices = filtered_df["topic"].tolist()
    selected_topic = st.selectbox("Select a task", task_choices)
    st.session_state.selected_topic = selected_topic

    # Step 4: Fill‑in‑the‑blank fields
    chosen_prompt = filtered_df[filtered_df["topic"] == selected_topic]
    prompt_text = chosen_prompt["prompt_text"].values[0]
    variables = chosen_prompt["variables"].values[0]

    st.subheader("Customize Your Prompt")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Fill in the blanks")
        for var in variables:
            helper_text = f"Enter your {var.replace('_', ' ').lower()} here."
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

    # --- Feedback Section (Expanded) ---
    st.subheader("We'd love your feedback")

    likert_options = [
        "Very easy",
        "Easy",
        "Neutral",
        "Difficult",
        "Very difficult",
    ]
    difficulty = st.select_slider(
        "Was this tool difficult to use?", options=likert_options, value="Neutral"
    )
    difficulty_more = st.text_area(
        "Optional: Tell us more.",
        # key="difficulty_more",
        placeholder="What worked well? What could be improved?",
    )

    hours_saved = st.number_input(
        "If you did this task manually without a prompt, about how many hours would it have taken?",
        min_value=0.0,
        step=0.5,
        help="Use your best estimate.",
        value=0.0,
    )

    frequency = st.selectbox(
        "How frequently do you execute this task?",
        [
            "Daily",
            "Multiple times per week",
            "Weekly",
            "Monthly",
            "Quarterly",
            "Ad hoc",
        ],
    )

    desired_integrations = st.text_area(
        "Are there tools or data sources you wish you could connect to the prompt for a better result? If so, which ones?",
        placeholder="e.g., Salesforce, Mailchimp, Google Sheets, internal database, etc.",
    )

    if st.button("Submit"):
        # st.success("Your response has been recorded.")

        # Compile all responses
        response = {
            "timestamp": datetime.now().isoformat(),
            "organization": st.session_state.contact.get("org"),
            "email": st.session_state.contact.get("email"),
            "role": st.session_state.contact.get("role"),
            "category": selected_category,
            "template": selected_template,
            "topic": selected_topic,
            "prompt": prompt_text,
            "final_prompt": final_prompt,
            # Feedback extras
            "difficulty_likert": difficulty,
            "difficulty_comments": difficulty_more,
            "hours_without_prompt": hours_saved,
            "task_frequency": frequency,
            "desired_integrations": desired_integrations,
            "time_taken_seconds": (
                time.time() - st.session_state.start_time
                if st.session_state.start_time
                else None
            ),
        }
        # update response with the landing_response info
        # response.update(landing_response)
        # st.write(response)  # For debugging; remove in production
        # st.write(landing_response)  # For debugging; remove in production
        try:
            supabase.table("responses").insert(response).execute()
            # st.success("Your Supabase response has been saved successfully!")
            st.success("Your response has been sent to TechImpact. Thank You!!!")

        except Exception as e:
            st.error(f"Error saving response in Supabase: {e}")

    if st.button("Reset and Start Over"):  # this part needs more testing and work
        var_list = [
            "selected_category",
            "selected_template",
            "selected_topic",
            "inputs",
            "difficulty",
            "difficulty_more",
            "hours_saved",
            "frequency",
            "desired_integrations",
            # not resetting contact info or start_time
        ]
        st.write("Resetting state...")
        for key in var_list:
            # st.session_state.pop(key, None) # works as is
            if key == "inputs":
                st.session_state[key] = {}

            else:
                st.session_state[key] = ""
        st.session_state.page = "main"
        st.success("State has been reset.")
        print("State reset, rerunning app...")
        st.rerun()
