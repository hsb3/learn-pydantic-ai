"""Lesson 11 — a friendly Streamlit frontend for the capstone agent.

A thin client over the FastAPI endpoints (`app.py`) — it speaks only HTTP,
so it knows nothing about Temporal or pydantic-ai. That's the point: the
durable workflow exposes a clean HTTP contract, and any frontend can drive it.

Run it (worker + API must be up — `make temporal-11-worker` + `make temporal-11-api`):

    make temporal-11-ui
    # or: uv run streamlit run tracks/02-temporal/lessons/11_capstone_fastapi/ui.py

Then open http://localhost:8501.
"""

from __future__ import annotations

import os
import time

import httpx
import streamlit as st

API = os.getenv("CAPSTONE_API_URL", "http://localhost:8001")
TEMPORAL_UI = os.getenv("TEMPORAL_UI_URL", "http://localhost:8080")
NAMESPACE = "learn-pydantic-ai"
POLL_SECONDS = 1.5

# Pipeline stages the workflow reports via its `status` query, in order.
STAGES = [
    "fetching_context",
    "clarifying",
    "researching",
    "writing",
    "awaiting_approval",
    "completed",
]

st.set_page_config(page_title="Durable Research Agent", page_icon="🔬")
ss = st.session_state
ss.setdefault("wf_id", None)

st.title("🔬 Durable Research Agent")
st.caption(f"FastAPI backend: `{API}`  ·  durable execution on Temporal")


def get_status(wf_id: str) -> dict | None:
    """Fetch live workflow state. Returns None on a transient read error."""
    try:
        r = httpx.get(f"{API}/research/{wf_id}", timeout=10)
        return r.json()
    except Exception:
        # Mid-write responses can briefly fail to parse — treat as "keep polling".
        return None


# ── Start a job ──────────────────────────────────────────────────────────────
with st.form("start"):
    topic = st.text_input("Research topic", value="the population and GDP of Japan")
    start = st.form_submit_button(
        "Start research", disabled=ss.wf_id is not None, type="primary"
    )
    if start and topic.strip():
        try:
            r = httpx.post(f"{API}/research", json={"topic": topic.strip()}, timeout=10)
            r.raise_for_status()
            ss.wf_id = r.json()["workflow_id"]
            st.rerun()
        except Exception as e:  # noqa: BLE001 — surface any connection/HTTP error
            st.error(f"Could not start a job via {API}: {e}")

if not ss.wf_id:
    st.info(
        "Enter a topic and click **Start research** to kick off a durable workflow."
    )
    st.stop()

# ── Live view of the running / paused / finished workflow ────────────────────
wf_id = ss.wf_id
st.markdown(
    f"**Workflow:** `{wf_id}`  ·  "
    f"[inspect history in the Temporal UI]"
    f"({TEMPORAL_UI}/namespaces/{NAMESPACE}/workflows/{wf_id})"
)

data = get_status(wf_id)
status = (data or {}).get("status", "starting")

# Progress bar across the known stages ("revising" maps onto the writing step).
bar_status = "writing" if status == "revising" else status
done = STAGES.index(bar_status) + 1 if bar_status in STAGES else 0
st.progress(done / len(STAGES), text=f"Status: **{status}**")

draft = (data or {}).get("draft")
final = (data or {}).get("final_report")

if status == "awaiting_approval":
    st.subheader("Draft — your review")
    st.write(draft or "_(draft not available)_")
    with st.form("review"):
        feedback = st.text_area(
            "Feedback",
            "looks good",
            help="Used as the approval note, the revision instructions, "
            "or the rejection reason — depending on which button you click.",
        )
        c1, c2, c3 = st.columns(3)
        approve = c1.form_submit_button("✅ Approve & finish", type="primary")
        revise = c2.form_submit_button("✏️ Request changes")
        reject = c3.form_submit_button("🛑 Reject")

    try:
        if approve:
            httpx.post(
                f"{API}/research/{wf_id}/approve", json={"note": feedback}, timeout=10
            ).raise_for_status()
            st.rerun()
        elif revise:
            if not feedback.strip():
                st.warning("Add feedback so the writer knows what to change.")
            else:
                httpx.post(
                    f"{API}/research/{wf_id}/revise",
                    json={"feedback": feedback},
                    timeout=10,
                ).raise_for_status()
                st.rerun()
        elif reject:
            httpx.post(
                f"{API}/research/{wf_id}/reject", json={"reason": feedback}, timeout=10
            ).raise_for_status()
            st.rerun()
    except Exception as e:  # noqa: BLE001
        st.error(f"Action failed: {e}")

elif status == "completed":
    report = final or draft or "_(empty)_"
    if report.startswith("REJECTED"):
        st.error("Rejected — closed without shipping")
        st.write(report)
    else:
        st.success("Completed")
        st.subheader("Final report")
        st.write(report)
    if st.button("Start another"):
        ss.wf_id = None
        st.rerun()

else:
    # Still working — show the draft if it exists yet, then poll again.
    if draft:
        with st.expander("Draft so far", expanded=False):
            st.write(draft)
    with st.spinner(f"Working… ({status})"):
        time.sleep(POLL_SECONDS)
    st.rerun()
