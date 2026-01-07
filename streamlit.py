import streamlit as st
import requests

st.set_page_config(page_title="AI Gateway", layout="centered")
st.title("🧠 AI Gateway – Company LLM Platform")

st.markdown("This UI only talks to your deployed FastAPI backend. All user handling & logging is done in MongoDB by the API.")

# =========================
# STEP 1 – API URL
# =========================
api_url = st.text_input(
    "Enter Deployed API Base URL",
    value="https://logs-mongodb.onrender.com",
    placeholder="https://logs-mongodb.onrender.com",
    help="Do NOT add /ask or /init_user"
)

# =========================
# STEP 2 – USER IDENTIFICATION
# =========================
st.subheader("👤 User Identification")

name = st.text_input("Name", placeholder="Anurag Rawat")
email = st.text_input("Email", placeholder="anurag@company.com")

continue_clicked = st.button("Continue")

if continue_clicked:
    if not api_url or not name or not email:
        st.error("Please enter API URL, Name, and Email.")
    else:
        try:
            with st.spinner("Verifying / creating user in backend..."):
                res = requests.post(
                    f"{api_url}/init_user",
                    json={
                        "name": name,
                        "email": email
                    },
                    timeout=30
                )

            if res.status_code == 200:
                data = res.json()
                st.success(data.get("message", "User verified"))
                st.session_state["email"] = email   # only to reuse in prompt call
                st.session_state["ready"] = True
            else:
                st.error(f"Backend error {res.status_code}: {res.text}")

        except Exception as e:
            st.error(f"Connection error: {str(e)}")

# =========================
# STEP 3 – ASK LLM
# =========================
if st.session_state.get("ready", False):

    st.divider()
    st.subheader("🚀 Ask AI")

    model_name = st.selectbox(
        "Select Model",
        ["gemini-2.5-flash", "gemini-2.5-pro","gemini-2.5-flash-lite"]
    )

    prompt = st.text_area(
        "Enter Prompt",
        height=160,
        placeholder="Ask anything..."
    )

    ask_clicked = st.button("Run Prompt")

    if ask_clicked:
        if not prompt:
            st.error("Please enter a prompt.")
        else:
            try:
                with st.spinner("Calling AI via backend..."):
                    res = requests.post(
                        f"{api_url}/ask",
                        json={
                            "email": st.session_state["email"],
                            "model_name": model_name,
                            "prompt": prompt
                        },
                        timeout=120
                    )

                if res.status_code == 200:
                    data = res.json()

                    # =======================
                    # RESPONSE
                    # =======================
                    st.subheader("💬 Response")
                    st.write(data["response"])

                    # =======================
                    # USAGE METRICS
                    # =======================
                    st.subheader("📊 Usage Metrics")

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Prompt Tokens", data.get("prompt_tokens", 0))
                    col2.metric("Response Tokens", data.get("response_tokens", 0))
                    col3.metric("Total Tokens", data.get("total_tokens", 0))

                    # =======================
                    # COST
                    # =======================
                    st.subheader("💰 Estimated Cost")
                    st.write(f"${data.get('estimated_cost', 0)}")

                else:
                    st.error(f"Backend error {res.status_code}: {res.text}")

            except Exception as e:
                st.error(f"Connection error: {str(e)}")
