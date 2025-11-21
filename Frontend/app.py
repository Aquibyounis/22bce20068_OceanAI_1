# Frontend/app.py
import streamlit as st
import requests
import os
import tempfile
from pathlib import Path
import json

# Backend host
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="QA Agent — Build KB & Agent", layout="wide")
st.title("QA Agent — Build KB (Phase 1) + Agent (Phase 2/3)")

# ---------------------
# Phase 1: Upload & Build KB
# ---------------------
st.header("1) Upload support documents (Phase 1)")
st.markdown("Upload MD/TXT/JSON/PDF etc. and optionally provide the checkout.html. When you click **Create KB**, the system will digest the documents and build the 'brain'.")

uploaded_files = st.file_uploader("Choose multiple support files (MD, TXT, JSON, PDF, etc.)", accept_multiple_files=True)

col1, col2 = st.columns(2)
with col1:
    html_upload = st.file_uploader("Upload checkout.html (optional)", type=["html", "htm"])
with col2:
    pasted_html = st.text_area("Or paste checkout.html content (optional)", height=180)

# REMOVED: Checkbox "Include checkout.html" (now handled automatically)

if st.button("Create KB (upload & build)"):
    if (not uploaded_files or len(uploaded_files) == 0) and (not pasted_html and not html_upload):
        st.warning("Upload at least one support doc or provide checkout.html.")
    else:
        files_payload = []
        tmp_paths = []
        
        # 1. Add uploaded support docs
        if uploaded_files:
            for f in uploaded_files:
                files_payload.append(("files", (f.name, f.getvalue(), f.type or "application/octet-stream")))
        
        # 2. Handle checkout.html (Upload has priority over Paste)
        if html_upload:
            files_payload.append(("files", (html_upload.name, html_upload.getvalue(), html_upload.type or "text/html")))
        elif pasted_html:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            tmp.write(pasted_html.encode("utf-8"))
            tmp.flush(); tmp.close()
            tmp_paths.append(tmp.name)
            with open(tmp.name, "rb") as b:
                files_payload.append(("files", ("checkout.html", b.read(), "text/html")))

        with st.spinner("Uploading files and building knowledge base (this may take a moment)..."):
            try:
                # Auto-set include_checkout_html to true. 
                # The backend will only find it if we actually added it to files_payload above.
                resp = requests.post(
                    f"{BACKEND}/upload_and_build",
                    files=files_payload,
                    data={"include_checkout_html": "true"}, 
                    timeout=600
                )
            except Exception as e:
                st.error("Failed to reach backend:")
                st.exception(e)
                resp = None

        # cleanup temp files
        for p in tmp_paths:
            try:
                os.unlink(p)
            except:
                pass

        if resp is None:
            pass
        elif resp.status_code != 200:
            st.error(f"Backend error: {resp.status_code}")
            try:
                st.text(resp.text)
            except:
                pass
        else:
            result = resp.json()
            proj = result.get("project_id")
            st.success("✅ Knowledge base created successfully.")
            st.info(f"Project ID: `{proj}` — keep this for Agent Mode (auto-saved).")
            st.json(result)
            st.session_state["last_project"] = proj

st.markdown("---")

# ---------------------
# Phase 2 & 3: Agent Mode
# ---------------------
st.header("Agent Mode — Generate Test Cases & Selenium Scripts (Phase 2 / 3)")

last_project = st.session_state.get("last_project", "")
project_id = st.text_input("Project ID (use the one returned after Create KB)", value=last_project, help="Example: proj_1763651092")

# Advanced options hidden by default
with st.expander("Advanced Options"):
    top_k = st.slider("Top-K retrieval (how many chunks to retrieve)", 1, 20, 6)

# REMOVED: "Generate ALL" section to prevent crashes.

st.subheader("Targeted Query")
st.markdown("Ask the agent to generate test cases for a specific feature.")

col_a, col_b = st.columns([3,1])
with col_a:
    # Default query updated to be more specific
    query = st.text_input("Query", value="Generate all positive and negative test cases for discount code")
with col_b:
    st.write("") # Spacer
    st.write("") 
    if st.button("Generate Test Cases", type="primary"):
        if not project_id:
            st.warning("Set or paste the project_id first.")
        elif not query:
            st.warning("Enter a query.")
        else:
            with st.spinner("Running RAG and generating testcases..."):
                payload = {"project_id": project_id, "query": query, "top_k": top_k}
                try:
                    # Timeout set to 600s (10 mins) to handle slow local LLMs
                    resp = requests.post(f"{BACKEND}/agent_query", json=payload, timeout=600)
                except Exception as e:
                    st.error("Agent request failed:")
                    st.exception(e)
                    resp = None

            if resp and resp.status_code == 200:
                try:
                    out = resp.json()
                    st.success("Agent returned results.")
                    st.session_state["last_agent_result"] = out
                except Exception as e:
                    st.error("Failed to parse JSON from backend:")
                    st.exception(e)
            else:
                st.error("Agent request failed or returned error.")
                if resp is not None:
                    st.text(resp.text)

# Display Results
agent_out = st.session_state.get("last_agent_result")
if agent_out:
    st.divider()
    st.subheader("Retrieved Evidence")
    retrieved = agent_out.get("retrieved", [])
    if not retrieved:
        st.write("No retrieved chunks returned.")
    else:
        for r in retrieved:
            md = r.get("metadata", {})
            src = md.get("source_document", "unknown")
            cid = md.get("chunk_id", "?")
            dist_val = r.get("distance")
            dist_str = f"{dist_val:.4f}" if isinstance(dist_val, (int, float)) else str(dist_val)
            with st.expander(f"📄 {src} :: chunk_{cid} (dist: {dist_str})"):
                st.write(r.get("text", ""))

    st.divider()
    st.subheader("Generated Test Cases")
    tc = agent_out.get("testcases")
    
    if isinstance(tc, dict) and tc.get("MISSING_DOCUMENTATION"):
        st.warning("MISSING_DOCUMENTATION: " + tc.get("MISSING_DOCUMENTATION"))
    else:
        # Handle list output
        if not isinstance(tc, list):
             st.write(tc)
        else:
            for i, t in enumerate(tc):
                with st.container():
                    # Header: Test ID + Feature
                    st.markdown(f"### 🔹 {t.get('Test_ID','TC-?')} : {t.get('Feature','')}")
                    
                    col_x, col_y = st.columns([2, 1])
                    with col_x:
                        st.markdown(f"**Test Scenario:** {t.get('Test_Scenario','')}")
                        st.markdown(f"**Expected Result:** {t.get('Expected_Result','')}")
                        st.markdown("**Steps:**")
                        steps = t.get("Steps", [])
                        if isinstance(steps, list):
                            for s_i, s in enumerate(steps, start=1):
                                st.markdown(f"{s_i}. {s}")
                        else:
                            st.write(str(steps))
                    
                    with col_y:
                        # Type Badge
                        t_type = t.get('Type','')
                        if "Positive" in t_type:
                            st.success(f"Type: {t_type}")
                        else:
                            st.error(f"Type: {t_type}")
                            
                        st.markdown("**Grounded In:**")
                        for g in t.get("Grounded_In", []):
                            st.code(g, language=None)
                    
                    # Script Generation Button
                    if st.button(f"Generate Selenium Script for {t.get('Test_ID')}", key=f"gen_{i}"):
                        with st.spinner("Generating Selenium script..."):
                            payload = {"project_id": project_id, "testcase": t}
                            try:
                                r2 = requests.post(f"{BACKEND}/generate_script", json=payload, timeout=600)
                            except Exception as e:
                                st.error("Script generation call failed:")
                                st.exception(e)
                                r2 = None

                        if r2 and r2.status_code == 200:
                            sc = r2.json()
                            if sc.get("status") in ("ok", "ok_unverified"):
                                code = sc.get("script")
                                st.subheader("Generated Selenium Script")
                                st.code(code, language="python")
                            else:
                                st.error("Script generation error:")
                                st.write(sc)
                        else:
                            st.error("Script generation failed.")
                            if r2: st.text(r2.text)
                st.markdown("---")