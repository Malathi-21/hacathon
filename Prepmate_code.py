
# streamlit run D:\OLD_FILES\genai\use_case4\hackathon\prepmate.py

import streamlit as st
import re
from openai import AzureOpenAI

# ---- Azure OpenAI Client Setup ----
client =AzureOpenAI(
api_key = "  ",
azure_endpoint = " ",
api_version = " "
)
MODEL = "gpt-4o-mini"  # <-- Use your Azure deployment name

# ---- Helper Functions ----
def gpt4o_agent(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()

def extract_questions(text):
    questions = re.findall(r"\d+\.\s*(.+?)(?=\n\d+\.|\Z)", text, re.DOTALL)
    if not questions:
        questions = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
    return questions[:5]

def extract_score(text):
    m = re.search(r"(\d+(\.\d+)?)", text)
    return float(m.group(1)) if m else None

# ---- Session State for Candidate Data ----
if "candidates" not in st.session_state:
    st.session_state["candidates"] = []
if "questions_in_progress" not in st.session_state:
    st.session_state["questions_in_progress"] = None
if "answers_in_progress" not in st.session_state:
    st.session_state["answers_in_progress"] = []
if "interview_step" not in st.session_state:
    st.session_state["interview_step"] = "start"
if "feedbacks_in_progress" not in st.session_state:
    st.session_state["feedbacks_in_progress"] = []
if "scores_in_progress" not in st.session_state:
    st.session_state["scores_in_progress"] = []
if "avg_score_in_progress" not in st.session_state:
    st.session_state["avg_score_in_progress"] = 0.0

# ---- Streamlit UI ----
st.set_page_config(page_title="Screening", layout="wide")
st.title("🤖PrepMate")

tab1, tab2, tab3 = st.tabs(["🎓 Candidate Interview", "💼 HR Screening", "🗂️ Candidate Records"])

# ---- Candidate Tab ----
with tab1:
    st.header("🎓 Candidate Mock Interview")
    # Step 1: Start Interview and Generate Questions
    if st.session_state["interview_step"] == "start":
        with st.form("candidate_form"):
            name = st.text_input("👤 Candidate Name")
            domain = st.text_input("📂 Domain (e.g., Data Science, Marketing)")
            resume = st.text_area("📄 Paste Resume", height=150)
            jd = st.text_area("📝 Paste Job Description", height=150)
            submitted = st.form_submit_button("🚀 Start Interview")

        if submitted:
            if not all([name, domain, resume, jd]):
                st.warning("Please fill all fields.")
                st.stop()
            # Generate questions (T1)
            jd_summary = gpt4o_agent(
                "You are an HR expert. Extract the key skills and focus areas from this job description.",
                jd
            )
            resume_summary = gpt4o_agent(
                "You are a career coach. Summarize the candidate’s key strengths and experience from this resume.",
                resume
            )
            insights = gpt4o_agent(
                "You are an expert at distilling information for interview question generation.",
                f"JD Analysis: {jd_summary}\nResume Analysis: {resume_summary}\n\nSummarize and synthesize the main insights for interview question generation."
            )
            questions_text = gpt4o_agent(
                "You are a technical interviewer. Based on the following insight, generate 5 different technical interview questions. Number each question.",
                f"Insight:\n{insights}"
            )
            questions = extract_questions(questions_text)
            st.session_state["questions_in_progress"] = {
                "name": name,
                "domain": domain,
                "resume": resume,
                "jd": jd,
                "questions": questions
            }
            st.session_state["answers_in_progress"] = [""] * len(questions)
            st.session_state["interview_step"] = "awaiting_answers"
            st.rerun()

    # Step 2: Candidate Answers Questions
    elif st.session_state["interview_step"] == "awaiting_answers":
        candidate = st.session_state["questions_in_progress"]
        st.markdown("### 📋 Mock Interview Questions")
        for idx, q in enumerate(candidate["questions"], 1):
            st.markdown(f"**Q{idx}:** {q}")
        st.markdown("---")
        st.markdown("### 🎤 Your Answers")
        all_answered = True
        for idx, q in enumerate(candidate["questions"], 1):
            ans = st.text_area(f"Your answer to Q{idx}:", key=f"answer_{idx}", value=st.session_state["answers_in_progress"][idx-1])
            st.session_state["answers_in_progress"][idx-1] = ans
            if not ans:
                all_answered = False
        if st.button("🧠 Get Feedback and Scores") and all_answered:
            feedbacks = []
            scores = []
            for idx, (q, ans) in enumerate(zip(candidate["questions"], st.session_state["answers_in_progress"]), 1):
                feedback = gpt4o_agent(
                    "You are a mock interview assessor. Evaluate the candidate's answer and provide constructive feedback.",
                    f"Question: {q}\nAnswer: {ans}"
                )
                score = gpt4o_agent(
                    "You are an AI evaluator. Give a performance rating out of 10 for the candidate's answer.",
                    f"Question: {q}\nAnswer: {ans}"
                )
                feedbacks.append(feedback)
                scores.append(extract_score(score))
            avg_score = sum(scores) / len(scores)
            # Store candidate data for HR tab
            st.session_state["candidates"].append({
                "name": candidate["name"],
                "domain": candidate["domain"],
                "resume": candidate["resume"],
                "jd": candidate["jd"],
                "questions": candidate["questions"],
                "answers": st.session_state["answers_in_progress"],
                "feedbacks": feedbacks,
                "scores": scores,
                "avg_score": avg_score
            })
            st.session_state["feedbacks_in_progress"] = feedbacks
            st.session_state["scores_in_progress"] = scores
            st.session_state["avg_score_in_progress"] = avg_score
            st.session_state["interview_step"] = "showing_feedback"
            st.rerun()
        elif st.button("Reset Interview"):
            st.session_state["questions_in_progress"] = None
            st.session_state["answers_in_progress"] = []
            st.session_state["interview_step"] = "start"
            st.rerun()

    # Step 3: Show Feedback and Scores
    elif st.session_state["interview_step"] == "showing_feedback":
        candidate = st.session_state["questions_in_progress"]
        feedbacks = st.session_state["feedbacks_in_progress"]
        scores = st.session_state["scores_in_progress"]
        avg_score = st.session_state["avg_score_in_progress"]
        st.success("Interview complete!")
        for i, (q, a, f, s) in enumerate(zip(candidate["questions"], st.session_state["answers_in_progress"], feedbacks, scores), 1):
            st.markdown(f"**Q{i}:** {q}")
            st.markdown(f"**Your answer:** {a}")
            st.markdown(f"**Feedback:** {f}")
            st.markdown(f"**Score:** {s} / 10")
            st.markdown("---")
        st.markdown(f"## 🏆 Average Score: {avg_score:.2f} / 10")
        if st.button("Restart"):
            st.session_state["questions_in_progress"] = None
            st.session_state["answers_in_progress"] = []
            st.session_state["feedbacks_in_progress"] = []
            st.session_state["scores_in_progress"] = []
            st.session_state["avg_score_in_progress"] = 0.0
            st.session_state["interview_step"] = "start"
            st.rerun()

# ---- HR Screening Tab ----
with tab2:
    st.header("💼 HR Candidate Shortlisting")
    hr_domain = st.text_input("Filter by Domain (e.g., Data Science):")
    min_score = st.slider("Minimum Average Score", 0, 10, 7)

    if st.button("🔎 Find Matching Candidates"):
        filtered = [
            c for c in st.session_state["candidates"]
            if hr_domain.lower() in c["domain"].lower() and c["avg_score"] >= min_score
        ]
        if filtered:
            st.success(f"Found {len(filtered)} candidate(s) matching your criteria.")
            for c in filtered:
                st.markdown(f"### 👤 {c['name']}")
                st.markdown(f"- Domain: {c['domain']}")
                st.markdown(f"- Average Score: {c['avg_score']:.2f}")
                with st.expander("Show Details"):
                    for i, (q, a, f, s) in enumerate(zip(c["questions"], c["answers"], c["feedbacks"], c["scores"]), 1):
                        st.markdown(f"**Q{i}:** {q}")
                        st.markdown(f"**Answer:** {a}")
                        st.markdown(f"**Feedback:** {f}")
                        st.markdown(f"**Score:** {s} / 10")
                        st.markdown("---")
        else:
            st.warning("No matching candidates found.")

st.markdown("---")
st.caption("Powered by Malathi")
with tab3:
    st.header("🗂️ Candidate Records")
    if st.session_state["candidates"]:
        # Prepare a summary DataFrame
        summary_data = [
            {
                "Name": c["name"],
                "Domain": c["domain"],
                "Average Score": round(c["avg_score"], 2)
            }
            for c in st.session_state["candidates"]
        ]
        st.dataframe(summary_data, use_container_width=True)
    else:
        st.info("No candidate records yet. Complete at least one interview to see records here.")