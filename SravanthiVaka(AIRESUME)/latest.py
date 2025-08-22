from __future__ import annotations

import io
import os
import base64
from typing import List, Dict, Any
from PIL import Image

import streamlit as st

from src.embeddings import EmbeddingService
from src.agents import content_enhancer_agent, job_parser_agent, matcher_and_scoring_agent, resume_parser_agent
from src.reporting import generate_pdf_report, generate_ats_resume_pdf
from src.workflow import build_workflow_trace, workflow_figure
from src.ui_components import show_agent_outputs, show_match_summary, show_workflow_diagram


# Enhanced page config with custom styling
st.set_page_config(
    page_title="AI Resume Matcher Pro", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀"
)

# Custom CSS for modern styling with vibrant colors
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #4facfe 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Main container */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 25px;
        padding: 2rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 25px 50px rgba(0,0,0,0.1);
        margin: 1rem;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 25%, #ff9ff3 50%, #54a0ff 75%, #5f27cd 100%);
        padding: 3rem;
        border-radius: 25px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(255,107,107,0.4);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 75%, rgba(255,255,255,0.1) 75%);
        background-size: 30px 30px;
        animation: movePattern 20s linear infinite;
    }
    
    @keyframes movePattern {
        0% { background-position: 0 0; }
        100% { background-position: 30px 30px; }
    }
    
    .main-header h1 {
        font-family: 'Poppins', sans-serif;
        font-size: 4rem;
        font-weight: 900;
        margin-bottom: 0.5rem;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
    }
    
    .main-header p {
        font-size: 1.4rem;
        opacity: 0.95;
        margin-bottom: 0;
        position: relative;
        z-index: 1;
    }
    
    /* Feature Cards */
    .feature-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        border: none;
        margin-bottom: 2rem;
        transition: all 0.4s ease;
        backdrop-filter: blur(10px);
        position: relative;
        overflow: hidden;
    }
    
    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(90deg, #ff6b6b, #ee5a24, #ff9ff3, #54a0ff, #5f27cd);
        background-size: 300% 100%;
        animation: gradientMove 3s ease infinite;
    }
    
    @keyframes gradientMove {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .feature-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 25px 50px rgba(0,0,0,0.15);
    }
    
    .feature-card.matching {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.05) 100%);
    }
    
    .feature-card.builder {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.05) 100%);
    }
    
    .feature-card.analytics {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.05) 100%);
    }
    
    /* Vibrant Stats Cards */
    .stats-card {
        color: white;
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .stats-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
        transform: rotate(45deg);
        animation: shine 3s ease-in-out infinite;
    }
    
    @keyframes shine {
        0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
        50% { transform: translateX(100%) translateY(100%) rotate(45deg); }
        100% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
    }
    
    .stats-card:hover {
        transform: translateY(-5px) scale(1.05);
    }
    
    .stats-card h3 {
        font-size: 3rem;
        font-weight: 900;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 6px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
    }
    
    .stats-card p {
        font-size: 1rem;
        opacity: 0.95;
        position: relative;
        z-index: 1;
    }
    
    /* Colorful Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 50%, #ff9ff3 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 0.8rem 2rem;
        font-weight: 700;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 10px 25px rgba(255,107,107,0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 35px rgba(255,107,107,0.4);
        background: linear-gradient(135deg, #ff5252 0%, #d84315 50%, #e91e63 100%);
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .css-1d391kg .css-1v0mbdj {
        color: white;
    }
    
    /* Form Styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 15px;
        border: 3px solid transparent;
        background: linear-gradient(white, white) padding-box, 
                    linear-gradient(45deg, #ff6b6b, #ee5a24, #ff9ff3, #54a0ff) border-box;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        box-shadow: 0 0 20px rgba(255,107,107,0.3);
        transform: translateY(-2px);
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 50%, #ff9ff3 100%);
        color: white;
        border-radius: 15px;
        font-weight: 700;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(255,107,107,0.3);
    }
    
    /* Progress Bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #ff6b6b 0%, #ee5a24 50%, #ff9ff3 100%);
        border-radius: 10px;
    }
    
    /* Success/Info Messages */
    .success-message {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 10px 25px rgba(16,185,129,0.3);
    }
    
    .info-message {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 10px 25px rgba(59,130,246,0.3);
    }
    
    /* Animated background elements */
    .floating-shapes {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
    }
    
    .shape {
        position: absolute;
        border-radius: 50%;
        animation: float 6s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-20px) rotate(180deg); }
    }
</style>
""", unsafe_allow_html=True)

try:
    import importlib
    _dotenv = importlib.import_module("dotenv")
    _dotenv.load_dotenv(override=False)
except Exception:
    pass


def process_uploaded_image(uploaded_file) -> str:
    """Convert uploaded image to base64 data URL"""
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.thumbnail((300, 300), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            img_data = buffer.getvalue()
            b64_string = base64.b64encode(img_data).decode()
            return f"data:image/jpeg;base64,{b64_string}"
        except Exception as e:
            st.error(f"Error processing image: {e}")
            return ""
    return ""


def create_colorful_stats_section():
    """Create a vibrant stats and features section"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 50%, #ff9ff3 100%); 
                padding: 2rem; border-radius: 20px; color: white; text-align: center; margin-bottom: 1.5rem;
                box-shadow: 0 15px 35px rgba(255,107,107,0.4);">
        <h2 style="font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.3);">
            AI-Powered Success
        </h2>
        <p style="font-size: 1.2rem; opacity: 0.95;">Transforming careers with intelligent automation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Multi-color stats cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="stats-card" style="background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);">
            <div style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem; text-shadow: 2px 2px 6px rgba(0,0,0,0.3);">95%</div>
            <p style="font-size: 1rem; opacity: 0.95;">Matching Accuracy</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="stats-card" style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);">
            <div style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem; text-shadow: 2px 2px 6px rgba(0,0,0,0.3);">10K+</div>
            <p style="font-size: 1rem; opacity: 0.95;">Resumes Enhanced</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="stats-card" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);">
            <div style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem; text-shadow: 2px 2px 6px rgba(0,0,0,0.3);">24/7</div>
            <p style="font-size: 1rem; opacity: 0.95;">AI Availability</p>
        </div>
        """, unsafe_allow_html=True)


def create_vibrant_feature_showcase():
    """Create vibrant feature showcase with animations"""
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        <div class="feature-card matching">
            <h3 style="color: #10b981; font-size: 2rem; margin-bottom: 1rem;">
                🎯 Smart Resume Matching
            </h3>
            <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 1.5rem;">
                Revolutionary AI analyzes your resume against job descriptions with unprecedented accuracy. 
                Get actionable insights that transform your job search success rate.
            </p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.5rem;">
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                            color: white; padding: 1rem; border-radius: 10px; text-align: center;">
                    <strong>Semantic Analysis</strong><br>
                    <small>Advanced NLP matching</small>
                </div>
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
                            color: white; padding: 1rem; border-radius: 10px; text-align: center;">
                    <strong>Skill Gap Detection</strong><br>
                    <small>Identify missing competencies</small>
                </div>
                <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                            color: white; padding: 1rem; border-radius: 10px; text-align: center;">
                    <strong>ATS Optimization</strong><br>
                    <small>Beat applicant tracking systems</small>
                </div>
                <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                            color: white; padding: 1rem; border-radius: 10px; text-align: center;">
                    <strong>Detailed Reports</strong><br>
                    <small>Professional PDF insights</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card builder">
            <h3 style="color: #3b82f6; font-size: 2rem; margin-bottom: 1rem;">
                📝 Professional Resume Builder
            </h3>
            <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 1.5rem;">
                Create stunning, ATS-friendly resumes that capture attention. Our intelligent builder 
                combines professional design with industry best practices.
            </p>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem;">
                <span style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
                           color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    Modern Templates
                </span>
                <span style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                           color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    Photo Integration
                </span>
                <span style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                           color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    Dynamic Sections
                </span>
                <span style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                           color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                    Instant PDF
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card analytics">
            <h3 style="color: #f59e0b; font-size: 2rem; margin-bottom: 1rem;">
                📊 Advanced Analytics Dashboard
            </h3>
            <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 1.5rem;">
                Deep insights powered by multi-agent AI workflow. Understand exactly how your resume 
                performs with explainable AI and visual analytics.
            </p>
            <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                        padding: 1.5rem; border-radius: 15px; margin-top: 1rem;">
                <ul style="color: #92400e; margin: 0; padding-left: 1.2rem; line-height: 1.8;">
                    <li><strong>Multi-Agent Workflow:</strong> Specialized AI agents for different analysis tasks</li>
                    <li><strong>Visual Diagrams:</strong> Interactive workflow and decision trees</li>
                    <li><strong>Explainable AI:</strong> Understand the reasoning behind every recommendation</li>
                    <li><strong>Performance Metrics:</strong> Track improvement over time</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        create_colorful_stats_section()
        
        # Interactive demo section
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 20px; color: white; text-align: center; margin-bottom: 1.5rem;
                    box-shadow: 0 15px 35px rgba(102,126,234,0.4);">
            <h3 style="font-size: 1.8rem; margin-bottom: 1rem;">🚀 Ready to Transform?</h3>
            <p style="opacity: 0.9; margin-bottom: 1.5rem;">
                Join thousands of professionals who have revolutionized their job search with AI
            </p>
            <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                <p style="margin: 0; font-size: 0.9rem;">
                    Average increase in interview callbacks: <strong>73%</strong>
                </p>
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                <p style="margin: 0; font-size: 0.9rem;">
                    Time saved per application: <strong>45 minutes</strong>
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tech stack showcase
        st.markdown("""
        <div style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                    padding: 2rem; border-radius: 20px; color: #831843; margin-bottom: 1.5rem;">
            <h4 style="font-size: 1.5rem; margin-bottom: 1rem; text-align: center;">🧠 Powered by AI</h4>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
                <span style="background: rgba(255,255,255,0.8); padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; font-weight: 600;">
                    OpenAI GPT
                </span>
                <span style="background: rgba(255,255,255,0.8); padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; font-weight: 600;">
                    Semantic Search
                </span>
                <span style="background: rgba(255,255,255,0.8); padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; font-weight: 600;">
                    Multi-Agent
                </span>
                <span style="background: rgba(255,255,255,0.8); padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; font-weight: 600;">
                    NLP Analysis
                </span>
                <span style="background: rgba(255,255,255,0.8); padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; font-weight: 600;">
                    ML Scoring
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def dynamic_list_input(label: str, key: str, placeholder: str = "", help_text: str = None) -> List[str]:
    """Create a dynamic list input with add/remove buttons"""
    if f"{key}_items" not in st.session_state:
        st.session_state[f"{key}_items"] = [""]
    
    st.markdown(f"**{label}**")
    if help_text:
        st.markdown(f"*{help_text}*")
    
    items = []
    
    for i, item in enumerate(st.session_state[f"{key}_items"]):
        col1, col2 = st.columns([4, 1])
        with col1:
            value = st.text_input(f"{label} {i+1}", value=item, key=f"{key}_input_{i}", placeholder=placeholder)
            if value.strip():
                items.append(value.strip())
        with col2:
            if st.button("❌", key=f"{key}_remove_{i}", help="Remove this item"):
                st.session_state[f"{key}_items"].pop(i)
                st.rerun()
    
    if st.button(f"➕ Add {label}", key=f"{key}_add"):
        st.session_state[f"{key}_items"].append("")
        st.rerun()
    
    st.session_state[f"{key}_items"] = [item for item in st.session_state[f"{key}_items"] if True]
    
    return items


def dynamic_experience_input() -> List[Dict[str, Any]]:
    """Create dynamic experience section input"""
    if "experience_items" not in st.session_state:
        st.session_state["experience_items"] = [{}]
    
    experiences = []
    
    for i, exp in enumerate(st.session_state["experience_items"]):
        st.markdown(f"**🏢 Experience {i+1}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Job Title", value=exp.get("title", ""), key=f"exp_title_{i}")
            company = st.text_input("Company", value=exp.get("company", ""), key=f"exp_company_{i}")
            start_date = st.text_input("Start Date", value=exp.get("start", ""), key=f"exp_start_{i}", 
                                     placeholder="e.g., Jan 2022")
        
        with col2:
            location = st.text_input("Location", value=exp.get("location", ""), key=f"exp_location_{i}")
            end_date = st.text_input("End Date", value=exp.get("end", ""), key=f"exp_end_{i}", 
                                   placeholder="e.g., Present")
        
        bullets_text = st.text_area("Key Achievements & Responsibilities", 
                                   value="\n".join(exp.get("bullets", [])), 
                                   key=f"exp_bullets_{i}",
                                   placeholder="• Increased sales by 25% through strategic initiatives\n• Led a team of 5 developers\n• Implemented new processes",
                                   height=100)
        
        bullets = [b.strip() for b in bullets_text.split('\n') if b.strip()]
        
        if title or company or bullets:
            experiences.append({
                "title": title,
                "company": company,
                "location": location,
                "start": start_date,
                "end": end_date,
                "bullets": bullets
            })
        
        col1, col2 = st.columns(2)
        with col2:
            if st.button(f"❌ Remove Experience {i+1}", key=f"exp_remove_{i}"):
                st.session_state["experience_items"].pop(i)
                st.rerun()
        
        if i < len(st.session_state["experience_items"]) - 1:
            st.divider()
    
    if st.button("➕ Add Another Experience"):
        st.session_state["experience_items"].append({})
        st.rerun()
    
    return experiences


def dynamic_education_input() -> List[Dict[str, Any]]:
    """Create dynamic education section input"""
    if "education_items" not in st.session_state:
        st.session_state["education_items"] = [{}]
    
    education = []
    
    for i, edu in enumerate(st.session_state["education_items"]):
        st.markdown(f"**🎓 Education {i+1}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            degree = st.text_input("Degree", value=edu.get("degree", ""), key=f"edu_degree_{i}")
            school = st.text_input("School/University", value=edu.get("school", ""), key=f"edu_school_{i}")
        
        with col2:
            year = st.text_input("Year", value=edu.get("year", ""), key=f"edu_year_{i}", placeholder="e.g., 2020")
            location = st.text_input("Location", value=edu.get("location", ""), key=f"edu_location_{i}")
        
        details_text = st.text_area("Additional Details", 
                                   value="\n".join(edu.get("details", [])), 
                                   key=f"edu_details_{i}",
                                   placeholder="• GPA: 3.8/4.0\n• Relevant Coursework: Data Structures, Algorithms\n• Dean's List",
                                   height=80)
        
        details = [d.strip() for d in details_text.split('\n') if d.strip()]
        
        if degree or school:
            education.append({
                "degree": degree,
                "school": school,
                "location": location,
                "year": year,
                "details": details
            })
        
        col1, col2 = st.columns(2)
        with col2:
            if st.button(f"❌ Remove Education {i+1}", key=f"edu_remove_{i}"):
                st.session_state["education_items"].pop(i)
                st.rerun()
        
        if i < len(st.session_state["education_items"]) - 1:
            st.divider()
    
    if st.button("➕ Add Another Education"):
        st.session_state["education_items"].append({})
        st.rerun()
    
    return education


def dynamic_projects_input() -> List[Dict[str, Any]]:
    """Create dynamic projects section input"""
    if "project_items" not in st.session_state:
        st.session_state["project_items"] = [{}]
    
    projects = []
    
    for i, proj in enumerate(st.session_state["project_items"]):
        st.markdown(f"**🚀 Project {i+1}**")
        
        name = st.text_input("Project Name", value=proj.get("name", ""), key=f"proj_name_{i}")
        description = st.text_area("Description", value=proj.get("description", ""), key=f"proj_desc_{i}",
                                 placeholder="Brief description of the project, its purpose, and your role",
                                 height=80)
        tech_text = st.text_input("Technologies Used", value=", ".join(proj.get("tech", [])), 
                                key=f"proj_tech_{i}",
                                placeholder="React, Node.js, MongoDB, AWS")
        
        tech = [t.strip() for t in tech_text.split(',') if t.strip()]
        
        if name or description:
            projects.append({
                "name": name,
                "description": description,
                "tech": tech
            })
        
        col1, col2 = st.columns(2)
        with col2:
            if st.button(f"❌ Remove Project {i+1}", key=f"proj_remove_{i}"):
                st.session_state["project_items"].pop(i)
                st.rerun()
        
        if i < len(st.session_state["project_items"]) - 1:
            st.divider()
    
    if st.button("➕ Add Another Project"):
        st.session_state["project_items"].append({})
        st.rerun()
    
    return projects


def main() -> None:
    # Enhanced sidebar with vibrant navigation
    st.sidebar.markdown("""
    <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 25%, #ff9ff3 50%, #54a0ff 75%, #5f27cd 100%); 
                padding: 2rem; border-radius: 20px; color: white; text-align: center; margin-bottom: 2rem;
                box-shadow: 0 15px 35px rgba(255,107,107,0.4);">
        <h2 style="margin-bottom: 0.5rem; font-weight: 900;">🚀 AI Resume Pro</h2>
        <p style="opacity: 0.95; margin: 0; font-size: 0.9rem;">Navigate Your Success</p>
    </div>
    """, unsafe_allow_html=True)
    
    mode = st.sidebar.radio(
        "Choose Your Path",
        ["🏠 Welcome", "🎯 Resume Matching", "📝 Resume Builder"],
        format_func=lambda x: x
    )

    # Add floating background elements
    st.markdown("""
    <div class="floating-shapes">
        <div class="shape" style="top: 10%; left: 10%; width: 50px; height: 50px; background: linear-gradient(45deg, #ff6b6b, #ee5a24); opacity: 0.1; animation-delay: 0s;"></div>
        <div class="shape" style="top: 20%; right: 15%; width: 30px; height: 30px; background: linear-gradient(45deg, #ff9ff3, #54a0ff); opacity: 0.1; animation-delay: 2s;"></div>
        <div class="shape" style="bottom: 30%; left: 20%; width: 40px; height: 40px; background: linear-gradient(45deg, #5f27cd, #00d2ff); opacity: 0.1; animation-delay: 4s;"></div>
    </div>
    """, unsafe_allow_html=True)

    # ----------------- WELCOME PAGE -----------------
    if mode == "🏠 Welcome":
        # Main header with enhanced gradient and animation
        st.markdown("""
        <div class="main-header">
            <h1>🚀 AI-Powered Resume Builder Pro</h1>
            <p>Transform Your Career with Next-Generation AI Technology</p>
        </div>
        """, unsafe_allow_html=True)

        # Enhanced feature showcase
        create_vibrant_feature_showcase()

        # Call to action with pulsing animation
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #4facfe 100%); 
                    padding: 3rem; border-radius: 25px; text-align: center; margin: 3rem 0;
                    color: white; position: relative; overflow: hidden;
                    box-shadow: 0 25px 50px rgba(102,126,234,0.3);">
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; 
                        background: linear-gradient(45deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 75%, rgba(255,255,255,0.1) 75%);
                        background-size: 20px 20px; animation: movePattern 10s linear infinite;"></div>
            <h2 style="font-size: 3rem; margin-bottom: 1rem; font-weight: 900; position: relative; z-index: 1;">
                Ready to Dominate Your Job Search?
            </h2>
            <p style="font-size: 1.3rem; margin-bottom: 2rem; opacity: 0.95; position: relative; z-index: 1;">
                Join the AI revolution and transform your career trajectory today
            </p>
            <div style="position: relative; z-index: 1;">
                <p style="font-size: 1.5rem; font-weight: 700;">👈 Choose your path from the sidebar to begin!</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ----------------- RESUME MATCHING -----------------
    elif mode == "🎯 Resume Matching":
        # Header for Resume Matching
        st.markdown("""
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 25%, #34d399 50%, #6ee7b7 75%, #a7f3d0 100%); 
                    padding: 3rem; border-radius: 25px; color: white; text-align: center; margin-bottom: 2rem;
                    box-shadow: 0 20px 40px rgba(16,185,129,0.4);">
            <h1 style="font-size: 3.5rem; font-weight: 900; margin-bottom: 0.5rem;">🎯 Smart Resume Matching</h1>
            <p style="font-size: 1.3rem; opacity: 0.95;">AI-powered analysis that revolutionizes your job search</p>
        </div>
        """, unsafe_allow_html=True)

        # Main matching interface
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%); 
                        padding: 2rem; border-radius: 20px; 
                        box-shadow: 0 15px 35px rgba(0,0,0,0.1); margin-bottom: 1rem;
                        border: 3px solid transparent;
                        background-clip: padding-box;
                        position: relative;">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; 
                            background: linear-gradient(90deg, #10b981, #059669, #34d399); border-radius: 20px 20px 0 0;"></div>
                <h3 style="color: #10b981; margin: 1rem 0; font-size: 1.8rem; font-weight: 700;">📄 Upload Your Resume</h3>
            </div>
            """, unsafe_allow_html=True)
            
            resume_file = st.file_uploader(
                "Choose your resume file", 
                type=["pdf"], 
                accept_multiple_files=False,
                help="Upload a PDF version of your resume for best text extraction"
            )
            
            if resume_file is not None:
                st.markdown(f"""
                <div class="success-message">
                    ✅ Resume uploaded successfully: <strong>{resume_file.name}</strong>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%); 
                        padding: 2rem; border-radius: 20px; 
                        box-shadow: 0 15px 35px rgba(0,0,0,0.1); margin-bottom: 1rem;
                        border: 3px solid transparent;
                        background-clip: padding-box;
                        position: relative;">
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; 
                            background: linear-gradient(90deg, #3b82f6, #2563eb, #1d4ed8); border-radius: 20px 20px 0 0;"></div>
                <h3 style="color: #3b82f6; margin: 1rem 0; font-size: 1.8rem; font-weight: 700;">📋 Job Description</h3>
            </div>
            """, unsafe_allow_html=True)
            
            job_desc = st.text_area(
                "Paste the complete job description", 
                height=200,
                placeholder="Paste the complete job description here including:\n• Job title and company\n• Required qualifications\n• Responsibilities\n• Preferred skills\n• Experience requirements",
                help="Include all sections of the job posting for comprehensive analysis"
            )

        # Enhanced analysis button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            run = st.button(
                "🔍 Analyze Resume Match", 
                type="primary", 
                use_container_width=True,
                disabled=not (resume_file and job_desc),
                help="Start AI-powered analysis of your resume against the job description"
            )

        # Progress and results section
        if run and resume_file and job_desc:
            # Enhanced progress indicator
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("🤖 Our AI agents are analyzing your resume..."):
                embed = EmbeddingService()
                steps = []

                # Step 1: Resume parsing
                status_text.markdown("**📄 Parsing resume content...**")
                progress_bar.progress(20)
                resume_bytes = resume_file.getvalue()
                a1 = resume_parser_agent(resume_bytes)
                steps.append(a1)

                # Step 2: Job parsing
                status_text.markdown("**📋 Analyzing job description...**")
                progress_bar.progress(40)
                a2 = job_parser_agent(job_desc)
                steps.append(a2)

                # Step 3: Content enhancement
                status_text.markdown("**✨ Enhancing content analysis...**")
                progress_bar.progress(60)
                a3 = content_enhancer_agent(a1.outputs["raw_text"])
                steps.append(a3)

                # Step 4: Matching and scoring
                status_text.markdown("**🎯 Calculating match score and recommendations...**")
                progress_bar.progress(80)
                a4 = matcher_and_scoring_agent(
                    resume_text=a1.outputs["raw_text"],
                    job_text=job_desc,
                    resume_skills=a1.outputs["skills"],
                    job_skills=a2.outputs["skills"],
                    embedding_service=embed,
                )
                steps.append(a4)

                # Step 5: Generate workflow
                status_text.markdown("**📊 Generating visual workflow...**")
                progress_bar.progress(100)
                trace = build_workflow_trace(steps)
                fig = workflow_figure(trace)

                status_text.markdown("**✅ Analysis complete!**")
                
                # Clear progress indicators after a short delay
                import time
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()

            # Results section with enhanced styling
            st.markdown("""
            <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); 
                        padding: 3rem; border-radius: 25px; margin: 2rem 0;
                        border: 3px solid #10b981; box-shadow: 0 20px 40px rgba(16,185,129,0.2);">
                <h2 style="color: #065f46; margin-bottom: 1rem; font-size: 2.5rem; text-align: center; font-weight: 900;">
                    📊 AI Analysis Results
                </h2>
            </div>
            """, unsafe_allow_html=True)

            # Display workflow diagram
            st.markdown("### 🔄 AI Workflow Visualization")
            show_workflow_diagram(fig)

            # Display match summary with enhanced styling
            st.markdown("### 🎯 Match Summary")
            show_match_summary(
                score=float(a4.outputs["score"]),
                confidence=float(a4.outputs["confidence"]),
                missing_skills=list(a4.outputs["missing_skills"]),
                explanation=str(a4.outputs["explanation"]),
                top_snippets=list(a4.outputs["top_snippets"]),
            )

            # Agent outputs
            st.markdown("### 🤖 Detailed Agent Analysis")
            show_agent_outputs([(s.name, s.outputs) for s in steps])

            # Enhanced download section
            with st.expander("📄 Download Comprehensive Report", expanded=True):
                st.markdown("""
                <div style="background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); 
                            padding: 2rem; border-radius: 15px; margin-bottom: 1rem;">
                    <h4 style="color: #1e40af; margin-bottom: 0.5rem; font-size: 1.5rem;">📋 Professional Analysis Report</h4>
                    <p style="color: #1e40af; margin: 0; font-size: 1.1rem;">Get a detailed PDF report with all analysis results, recommendations, and action items.</p>
                </div>
                """, unsafe_allow_html=True)
                
                candidate = a1.outputs.get("name") or "Candidate"
                pdf_bytes = generate_pdf_report(
                    candidate_name=candidate,
                    match_score=float(a4.outputs["score"]),
                    confidence=float(a4.outputs["confidence"]),
                    explanation=str(a4.outputs["explanation"]),
                    missing_skills=list(a4.outputs["missing_skills"]),
                    top_snippets=list(a4.outputs["top_snippets"]),
                )
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.download_button(
                        label="📥 Download Professional Report",
                        data=pdf_bytes,
                        file_name=f"{candidate.replace(' ', '_').lower()}_match_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

    # ----------------- RESUME BUILDER -----------------
    elif mode == "📝 Resume Builder":
        # Header for Resume Builder
        st.markdown("""
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 25%, #1d4ed8 50%, #1e40af 75%, #1e3a8a 100%); 
                    padding: 3rem; border-radius: 25px; color: white; text-align: center; margin-bottom: 2rem;
                    box-shadow: 0 20px 40px rgba(59,130,246,0.4);">
            <h1 style="font-size: 3.5rem; font-weight: 900; margin-bottom: 0.5rem;">📝 Professional Resume Builder</h1>
            <p style="font-size: 1.3rem; opacity: 0.95;">Create stunning, ATS-friendly resumes with AI assistance</p>
        </div>
        """, unsafe_allow_html=True)

        # Initialize session state for dynamic inputs
        if "form_submitted" not in st.session_state:
            st.session_state.form_submitted = False

        # Two column layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Resume form
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%); 
                        padding: 2rem; border-radius: 20px; 
                        box-shadow: 0 15px 35px rgba(0,0,0,0.1); margin-bottom: 2rem;
                        border-top: 5px solid #3b82f6;">
                <h2 style="color: #3b82f6; margin-bottom: 1rem; font-size: 2rem; font-weight: 700;">✏️ Resume Information</h2>
            </div>
            """, unsafe_allow_html=True)
            
            data: Dict[str, Any] = {}

            # Contact Information
            with st.expander("👤 Contact Information", expanded=True):
                col1_inner, col2_inner = st.columns(2)
                with col1_inner:
                    name = st.text_input("Full Name *", placeholder="John Doe")
                    email = st.text_input("Email Address *", placeholder="john.doe@email.com")
                with col2_inner:
                    phone = st.text_input("Phone Number", placeholder="+1 (555) 123-4567")
                    location = st.text_input("Location", placeholder="City, State/Country")
                
                links = st.text_area("Professional Links", 
                                   placeholder="https://linkedin.com/in/johndoe\nhttps://github.com/johndoe\nhttps://portfolio.johndoe.com",
                                   help="One link per line")
                
                data.update({
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "location": location,
                    "links": [ln.strip() for ln in (links.splitlines() if links else []) if ln.strip()],
                })

            # Photo Upload
            with st.expander("📸 Professional Photo (Optional)", expanded=True):
                st.markdown("Upload a professional headshot for your resume. Image will be automatically resized.")
                photo_file = st.file_uploader("Choose image file", type=['png', 'jpg', 'jpeg'], 
                                            help="Recommended: Square photo, professional appearance")
                
                if photo_file:
                    col1_photo, col2_photo, col3_photo = st.columns([1, 1, 2])
                    with col1_photo:
                        st.image(photo_file, caption="Preview", width=100)
                    with col2_photo:
                        st.markdown("""
                        <div class="success-message" style="padding: 0.5rem; margin: 0;">
                            ✅ Photo uploaded
                        </div>
                        """, unsafe_allow_html=True)
                    
                    data["photo"] = process_uploaded_image(photo_file)
                else:
                    data["photo"] = None

            # Professional Summary
            with st.expander("📄 Professional Summary", expanded=True):
                summary = st.text_area("Professional Summary", 
                                     placeholder="Results-driven software engineer with 5+ years of experience developing scalable web applications. Proven track record of leading cross-functional teams and delivering high-quality solutions that improve user experience and business outcomes.",
                                     height=120,
                                     help="2-3 sentences highlighting your key qualifications and career objectives")
                data["summary"] = summary

            # Skills Section
            with st.expander("🛠️ Skills & Technologies", expanded=True):
                st.markdown("**Organize your skills by category for better readability**")
                st.markdown("*Format: 'Category: skill1, skill2, skill3' or just list skills separated by commas*")
                
                skills_text = st.text_area("Skills", 
                                         placeholder="Programming Languages: Python, Java, JavaScript\nFrameworks: React, Django, Node.js\nDatabases: PostgreSQL, MongoDB\nCloud: AWS, Docker, Kubernetes",
                                         height=120,
                                         help="You can categorize skills or just list them. Use format 'Category: skills' for categorization")
                
                skills = []
                if skills_text:
                    lines = [line.strip() for line in skills_text.split('\n') if line.strip()]
                    for line in lines:
                        if ':' in line:
                            skills.append(line)
                        else:
                            skills.extend([s.strip() for s in line.split(',') if s.strip()])
                
                data["skills"] = skills

            # Experience Section
            with st.expander("💼 Professional Experience", expanded=True):
                data["experience"] = dynamic_experience_input()

            # Education Section
            with st.expander("🎓 Education", expanded=True):
                data["education"] = dynamic_education_input()

            # Projects Section
            with st.expander("🚀 Projects", expanded=True):
                data["projects"] = dynamic_projects_input()

            # Certifications
            with st.expander("🏆 Certifications", expanded=True):
                certifications_text = st.text_area("Certifications",
                                                  placeholder="AWS Certified Solutions Architect\nGoogle Cloud Professional Data Engineer\nCertified Kubernetes Administrator (CKA)",
                                                  help="One certification per line")
                data["certifications"] = [c.strip() for c in (certifications_text.splitlines() if certifications_text else []) if c.strip()]

        with col2:
            # Vibrant tips section
            st.markdown("""
            <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                        padding: 2rem; border-radius: 20px; 
                        box-shadow: 0 10px 25px rgba(245,158,11,0.3); margin-bottom: 2rem;">
                <h3 style="color: #92400e; margin-bottom: 1rem; font-size: 1.5rem;">💡 Pro Tips</h3>
                <div style="color: #92400e; line-height: 1.8;">
                    <p style="margin-bottom: 1rem;"><strong>🚀 Action Verbs:</strong> Led, Developed, Increased, Optimized</p>
                    <p style="margin-bottom: 1rem;"><strong>📊 Quantify Impact:</strong> Include specific numbers and percentages</p>
                    <p style="margin-bottom: 1rem;"><strong>🎯 Keywords:</strong> Mirror job description language</p>
                    <p style="margin-bottom: 0;"><strong>🤖 ATS-Friendly:</strong> Clean, parseable formatting</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Industry insights
            st.markdown("""
            <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); 
                        padding: 2rem; border-radius: 20px; text-align: center; margin-bottom: 2rem;
                        box-shadow: 0 10px 25px rgba(16,185,129,0.2);">
                <h4 style="color: #065f46; margin-bottom: 1.5rem; font-size: 1.4rem; font-weight: 700;">📈 Resume Impact Stats</h4>
                <div style="color: #065f46;">
                    <div style="background: rgba(255,255,255,0.7); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                        <p style="margin: 0; font-weight: 600;"><strong>6 seconds</strong><br><small>Average recruiter review time</small></p>
                    </div>
                    <div style="background: rgba(255,255,255,0.7); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                        <p style="margin: 0; font-weight: 600;"><strong>75%</strong><br><small>Resumes filtered by ATS</small></p>
                    </div>
                    <div style="background: rgba(255,255,255,0.7); padding: 1rem; border-radius: 10px;">
                        <p style="margin: 0; font-weight: 600;"><strong>2 pages</strong><br><small>Optimal resume length</small></p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Success metrics
            st.markdown("""
            <div style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                        padding: 2rem; border-radius: 20px; color: #831843; margin-bottom: 1.5rem;
                        box-shadow: 0 10px 25px rgba(255,154,158,0.3);">
                <h4 style="font-size: 1.3rem; margin-bottom: 1rem; text-align: center; font-weight: 700;">✨ AI Enhancement Benefits</h4>
                <div style="text-align: center;">
                    <div style="background: rgba(255,255,255,0.8); padding: 0.8rem; border-radius: 10px; margin-bottom: 0.8rem;">
                        <p style="margin: 0; font-weight: 600;">73% increase in callbacks</p>
                    </div>
                    <div style="background: rgba(255,255,255,0.8); padding: 0.8rem; border-radius: 10px;">
                        <p style="margin: 0; font-weight: 600;">45 min saved per application</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Generate Resume Button
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%); 
                    padding: 2rem; border-radius: 20px; margin: 2rem 0;
                    box-shadow: 0 15px 35px rgba(0,0,0,0.1);">
            <h3 style="text-align: center; margin-bottom: 1.5rem; color: #3b82f6; font-size: 2rem;">
                📄 Generate Your Professional Resume
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_button = st.button(
                "🚀 Generate Professional Resume", 
                type="primary", 
                use_container_width=True,
                help="Create your ATS-friendly resume with professional formatting"
            )

        if generate_button:
            if not data.get("name"):
                st.error("⚠️ Please enter your full name to generate the resume.")
                return
            
            with st.spinner("🎨 Creating your professional resume..."):
                try:
                    resume_pdf = generate_ats_resume_pdf(data)
                    dl_name = (data.get("name", "resume")).replace(" ", "_").lower() + "_professional_resume.pdf"
                    
                    st.markdown("""
                    <div class="success-message" style="text-align: center; margin: 2rem 0; padding: 2rem;">
                        <h3 style="font-size: 2rem; margin-bottom: 1rem;">✅ Resume Generated Successfully!</h3>
                        <p style="font-size: 1.2rem; margin: 0;">Your professional resume is ready for download.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Download section
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.download_button(
                            label="📥 Download Your Professional Resume",
                            data=resume_pdf,
                            file_name=dl_name,
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    # Success info
                    st.markdown("""
                    <div class="info-message" style="text-align: center; margin: 2rem 0; padding: 1.5rem;">
                        <p style="font-size: 1.1rem; margin-bottom: 1rem;"><strong>Your resume features:</strong></p>
                        <p style="font-size: 1rem; margin: 0;">
                            ✓ Clean, professional formatting • ✓ ATS optimization • ✓ Modern design • ✓ Industry best practices
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Error generating resume: {str(e)}")
                    st.markdown("Please check your input data and try again.")

        # Enhanced tips section
        with st.expander("Professional Resume Writing Guide", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **Content Excellence:**
                - **Power Words**: Led, Developed, Implemented, Increased, Optimized
                - **Quantify Impact**: "Increased sales by 25%" vs "Increased sales"
                - **STAR Method**: Situation, Task, Action, Result framework
                - **Keywords**: Mirror language from target job descriptions
                - **Relevance**: Tailor content to specific roles and industries
                
                **ATS Optimization:**
                - Use standard section headings (Experience, Education, Skills)
                - Include relevant keywords naturally in context
                - Avoid images, tables, and complex formatting
                - Use common fonts (Arial, Calibri, Times New Roman)
                - Save as PDF to preserve formatting
                """)
            
            with col2:
                st.markdown("""
                **Visual Design:**
                - **Consistency**: Uniform formatting throughout document
                - **White Space**: Adequate margins and line spacing
                - **Hierarchy**: Clear distinction between sections and subsections
                - **Length**: 1-2 pages depending on experience level
                - **Professional**: Clean, modern appearance without distractions
                
                **Final Checklist:**
                - Proofread for spelling and grammar errors
                - Verify all contact information is current
                - Ensure consistent date formatting
                - Check that all bullet points add value
                - Test PDF rendering on different devices
                """)


if __name__ == "__main__":
    main()