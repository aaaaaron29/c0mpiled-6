"""Team Management page."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
import datetime
from app.theme import page_header, metric_card, badge, COLORS, inject_css

st.set_page_config(page_title="Team Management — ResearchOS", page_icon="👥", layout="wide")

page_header("Team Management", "Manage team members, roles, and research tasks.", "👥")

inject_css()

ROLES = ["PI", "Postdoc", "PhD Student", "Masters Student", "Undergrad", "Research Assistant"]
MODULES = ["Data Cleaning", "Data Labeling", "Review Queue", "Hypothesis Validator", "Contradiction Detector", "Replicability Scorer", "Design Critic"]
STATUSES = ["To Do", "In Progress", "Done", "Review"]
STATUS_COLORS = {
    "To Do": COLORS["neutral"],
    "In Progress": COLORS["primary"],
    "Done": COLORS["success"],
    "Review": COLORS["warning"],
}

# Initialize session state
if "team_data" not in st.session_state:
    st.session_state["team_data"] = {
        "team_name": "Research Team",
        "members": [],
        "tasks": [],
    }

team = st.session_state["team_data"]

# Team name
team_name = st.text_input("Team Name", value=team["team_name"])
team["team_name"] = team_name

tab_members, tab_tasks, tab_dashboard = st.tabs(["👤 Members", "📋 Tasks", "📊 Dashboard"])

# ---- Members Tab ----
with tab_members:
    st.subheader("Team Members")

    # Add member form
    with st.form("add_member"):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_name = st.text_input("Name")
        with col2:
            new_role = st.selectbox("Role", ROLES)
        with col3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Add Member", use_container_width=True)

        if submitted:
            if new_name.strip():
                team["members"].append({"name": new_name.strip(), "role": new_role})
                st.success(f"Added {new_name} as {new_role}")
                st.rerun()
            else:
                st.warning("Enter a name.")

    # Members list
    if not team["members"]:
        st.info("No team members yet. Add your first member above.")
    else:
        for i, member in enumerate(team["members"]):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{member['name']}**")
            with col2:
                st.markdown(badge(member["role"], COLORS["primary"]), unsafe_allow_html=True)
            with col3:
                if st.button("Remove", key=f"rm_member_{i}"):
                    team["members"].pop(i)
                    st.rerun()

# ---- Tasks Tab ----
with tab_tasks:
    st.subheader("Tasks")

    # Add task form
    member_names = [m["name"] for m in team["members"]] or ["(no members)"]
    with st.form("add_task"):
        col1, col2 = st.columns(2)
        with col1:
            task_assignee = st.selectbox("Assignee", member_names)
            task_module = st.selectbox("Module", MODULES)
        with col2:
            task_desc = st.text_area("Description", height=80)
            task_status = st.selectbox("Status", STATUSES)

        if st.form_submit_button("Add Task", use_container_width=True):
            if task_desc.strip():
                team["tasks"].append({
                    "assignee": task_assignee,
                    "module": task_module,
                    "description": task_desc.strip(),
                    "status": task_status,
                    "created_at": datetime.datetime.now().isoformat()[:19],
                })
                st.success("Task added!")
                st.rerun()
            else:
                st.warning("Enter a task description.")

    # Task list
    if not team["tasks"]:
        st.info("No tasks yet. Create your first task above.")
    else:
        # Filter
        filter_status = st.multiselect("Filter by status", STATUSES, default=[])
        filter_assignee = st.multiselect("Filter by assignee", member_names, default=[])

        filtered = team["tasks"]
        if filter_status:
            filtered = [t for t in filtered if t["status"] in filter_status]
        if filter_assignee:
            filtered = [t for t in filtered if t["assignee"] in filter_assignee]

        for i, task in enumerate(filtered):
            # Find original index
            orig_idx = team["tasks"].index(task)
            color = STATUS_COLORS.get(task["status"], COLORS["neutral"])
            with st.expander(f"{badge(task['status'], color)} {task['assignee']} — {task['module']} — {task['description'][:50]}", expanded=False):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown(f"**Description:** {task['description']}")
                    st.caption(f"Created: {task['created_at']}")
                with col2:
                    new_status = st.selectbox("Update Status", STATUSES, index=STATUSES.index(task["status"]), key=f"status_{orig_idx}")
                    if new_status != task["status"]:
                        team["tasks"][orig_idx]["status"] = new_status
                        st.rerun()
                with col3:
                    if st.button("Delete", key=f"del_task_{orig_idx}"):
                        team["tasks"].pop(orig_idx)
                        st.rerun()

# ---- Dashboard Tab ----
with tab_dashboard:
    st.subheader("Team Dashboard")

    members_count = len(team["members"])
    tasks_count = len(team["tasks"])
    done_count = len([t for t in team["tasks"] if t["status"] == "Done"])
    in_progress = len([t for t in team["tasks"] if t["status"] == "In Progress"])

    cols = st.columns(4)
    with cols[0]: metric_card("Members", members_count)
    with cols[1]: metric_card("Total Tasks", tasks_count)
    with cols[2]: metric_card("Completed", done_count, color=COLORS["success"])
    with cols[3]: metric_card("In Progress", in_progress, color=COLORS["primary"])

    if team["tasks"]:
        # Status breakdown
        st.subheader("Tasks by Status")
        for status in STATUSES:
            count = len([t for t in team["tasks"] if t["status"] == status])
            if count > 0:
                color = STATUS_COLORS.get(status, COLORS["neutral"])
                pct = int(count / max(tasks_count, 1) * 100)
                st.markdown(f"{badge(status, color)} **{count}** tasks ({pct}%)", unsafe_allow_html=True)

        # Per-member breakdown
        st.subheader("Tasks by Member")
        for member in team["members"]:
            member_tasks = [t for t in team["tasks"] if t["assignee"] == member["name"]]
            if member_tasks:
                done = len([t for t in member_tasks if t["status"] == "Done"])
                total = len(member_tasks)
                with st.expander(f"**{member['name']}** ({member['role']}) — {done}/{total} done"):
                    for t in member_tasks:
                        color = STATUS_COLORS.get(t["status"], COLORS["neutral"])
                        st.markdown(f"{badge(t['status'], color)} `{t['module']}` — {t['description'][:60]}", unsafe_allow_html=True)
    else:
        st.info("No tasks to display. Add tasks in the Tasks tab.")
