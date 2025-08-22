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

# Custom CSS for modern styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
        margin-bottom: 0;
    }
    
    /* Feature Cards */
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        border-left: 5px solid;
        margin-bottom: 1.5rem;
        transition: transform 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
    }
    
    .feature-card.matching {
        border-left-color: #4CAF50;
        background: linear-gradient(135deg, #f8fff8 0%, #e8f8e8 100%);
    }
    
    .feature-card.builder {
        border-left-color: #2196F3;
        background: linear-gradient(135deg, #f0f8ff 0%, #e0f0ff 100%);
    }
    
    .feature-card.analytics {
        border-left-color: #FF9800;
        background: linear-gradient(135deg, #fff8f0 0%, #ffe8d0 100%);
    }
    
    /* Stats Cards */
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .stats-card h3 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .stats-card p {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Resume Preview */
    .resume-preview {
        background: white;
        border: 2px dashed #e0e0e0;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    
    .resume-preview img {
        max-width: 100%;
        height: auto;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    /* Colorful Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9ff 0%, #f0f4ff 100%);
    }
    
    /* Progress Bars */
    .progress-bar {
        background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        height: 8px;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    
    /* Form Styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Alert Styling */
    .stAlert {
        border-radius: 10px;
    }
    
    /* Success Message */
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        color: #155724;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    
    /* Info Message */
    .info-message {
        background: linear-gradient(135deg, #cce7ff 0%, #b3d9ff 100%);
        color: #004085;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #007bff;
        margin: 1rem 0;
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


def create_resume_preview_section():
    """Create a resume preview section with sample images"""
    st.markdown("### ✨ Professional Resume Templates")
    st.markdown("*Our AI creates modern, ATS-friendly resumes that get noticed*")
    
    # Create three columns for resume templates
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                    width: 100%; height: 280px; border-radius: 10px; 
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    display: flex; flex-direction: column; padding: 1rem; margin-bottom: 1rem;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        height: 40px; border-radius: 5px; margin-bottom: 1rem;
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                John Doe
            </div>
            <div style="background: #e9ecef; height: 8px; border-radius: 4px; margin-bottom: 0.5rem;"></div>
            <div style="background: #e9ecef; height: 8px; border-radius: 4px; margin-bottom: 0.5rem; width: 80%;"></div>
            <div style="background: #e9ecef; height: 8px; border-radius: 4px; margin-bottom: 1rem; width: 60%;"></div>
            <div style="background: #667eea; height: 20px; border-radius: 3px; margin-bottom: 0.5rem; opacity: 0.7;"></div>
            <div style="background: #e9ecef; height: 6px; border-radius: 3px; margin-bottom: 0.3rem;"></div>
            <div style="background: #e9ecef; height: 6px; border-radius: 3px; margin-bottom: 0.3rem; width: 90%;"></div>
            <div style="background: #e9ecef; height: 6px; border-radius: 3px; margin-bottom: 1rem; width: 70%;"></div>
            <div style="background: #764ba2; height: 20px; border-radius: 3px; margin-bottom: 0.5rem; opacity: 0.7;"></div>
            <div style="background: #e9ecef; height: 6px; border-radius: 3px; margin-bottom: 0.3rem;"></div>
            <div style="background: #e9ecef; height: 6px; border-radius: 3px; width: 85%;"></div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fff8f0 0%, #ffe8d0 100%); 
                    width: 100%; height: 280px; border-radius: 10px; 
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    display: flex; flex-direction: column; padding: 1rem; margin-bottom: 1rem;">
            <div style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); 
                        height: 40px; border-radius: 5px; margin-bottom: 1rem;
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                Jane Smith
            </div>
            <div style="background: #FFE0B2; height: 8px; border-radius: 4px; margin-bottom: 0.5rem;"></div>
            <div style="background: #FFE0B2; height: 8px; border-radius: 4px; margin-bottom: 0.5rem; width: 75%;"></div>
            <div style="background: #FFE0B2; height: 8px; border-radius: 4px; margin-bottom: 1rem; width: 90%;"></div>
            <div style="background: #FF9800; height: 20px; border-radius: 3px; margin-bottom: 0.5rem; opacity: 0.8;"></div>
            <div style="background: #FFE0B2; height: 6px; border-radius: 3px; margin-bottom: 0.3rem;"></div>
            <div style="background: #FFE0B2; height: 6px; border-radius: 3px; margin-bottom: 0.3rem; width: 95%;"></div>
            <div style="background: #FFE0B2; height: 6px; border-radius: 3px; margin-bottom: 1rem; width: 80%;"></div>
            <div style="background: #F57C00; height: 20px; border-radius: 3px; margin-bottom: 0.5rem; opacity: 0.8;"></div>
            <div style="background: #FFE0B2; height: 6px; border-radius: 3px; margin-bottom: 0.3rem;"></div>
            <div style="background: #FFE0B2; height: 6px; border-radius: 3px; width: 88%;"></div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f0f8ff 0%, #e0f0ff 100%); 
                    width: 100%; height: 280px; border-radius: 10px; 
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    display: flex; flex-direction: column; padding: 1rem; margin-bottom: 1rem;">
            <div style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); 
                        height: 40px; border-radius: 5px; margin-bottom: 1rem;
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                Alex Johnson
            </div>
            <div style="background: #BBDEFB; height: 8px; border-radius: 4px; margin-bottom: 0.5rem;"></div>
            <div style="background: #BBDEFB; height: 8px; border-radius: 4px; margin-bottom: 0.5rem; width: 85%;"></div>
            <div style="background: #BBDEFB; height: 8px; border-radius: 4px; margin-bottom: 1rem; width: 70%;"></div>
            <div style="background: #2196F3; height: 20px; border-radius: 3px; margin-bottom: 0.5rem; opacity: 0.8;"></div>
            <div style="background: #BBDEFB; height: 6px; border-radius: 3px; margin-bottom: 0.3rem;"></div>
            <div style="background: #BBDEFB; height: 6px; border-radius: 3px; margin-bottom: 0.3rem; width: 92%;"></div>
            <div style="background: #BBDEFB; height: 6px; border-radius: 3px; margin-bottom: 1rem; width: 75%;"></div>
            <div style="background: #1976D2; height: 20px; border-radius: 3px; margin-bottom: 0.5rem; opacity: 0.8;"></div>
            <div style="background: #BBDEFB; height: 6px; border-radius: 3px; margin-bottom: 0.3rem;"></div>
            <div style="background: #BBDEFB; height: 6px; border-radius: 3px; width: 87%;"></div>
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
    # Enhanced sidebar with colorful navigation
    st.sidebar.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;">
        <h2 style="margin-bottom: 0.5rem;">🚀 AI Resume Pro</h2>
        <p style="opacity: 0.9; margin: 0;">Navigate Your Success</p>
    </div>
    """, unsafe_allow_html=True)
    
    mode = st.sidebar.radio(
        "Choose Your Path",
        ["🏠 Welcome", "🎯 Resume Matching", "📝 Resume Builder"],
        format_func=lambda x: x
    )

    # ----------------- WELCOME PAGE -----------------
    if mode == "🏠 Welcome":
        # Main header with gradient
        st.markdown("""
        <div class="main-header">
            <h1>🚀 AI-Powered Resume Builder Pro</h1>
            <p>Transform Your Career with Intelligent Resume Matching & Professional Building</p>
        </div>
        """, unsafe_allow_html=True)

        # Feature cards in columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Feature cards
            st.markdown("""
            <div class="feature-card matching">
                <h3>🎯 Smart Resume Matching</h3>
                <p>Our AI analyzes your resume against job descriptions with 95% accuracy. Get detailed insights, missing skills analysis, and personalized recommendations to boost your application success rate.</p>
                <ul style="margin-top: 1rem; color: #2e7d32;">
                    <li>✅ Semantic matching with confidence scores</li>
                    <li>✅ Missing skills identification</li>
                    <li>✅ ATS optimization recommendations</li>
                    <li>✅ Detailed PDF reports</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="feature-card builder">
                <h3>📝 Professional Resume Builder</h3>
                <p>Create stunning, ATS-friendly resumes with our intelligent builder. Multiple templates, dynamic sections, and professional formatting that gets you noticed by recruiters.</p>
                <ul style="margin-top: 1rem; color: #1565c0;">
                    <li>✅ Modern, professional templates</li>
                    <li>✅ Photo upload capability</li>
                    <li>✅ Dynamic sections (experience, projects, etc.)</li>
                    <li>✅ Instant PDF generation</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="feature-card analytics">
                <h3>📊 Advanced Analytics</h3>
                <p>Deep insights into your resume performance. Multi-agent workflow provides explainable results with visual workflow diagrams and comprehensive analysis.</p>
                <ul style="margin-top: 1rem; color: #ef6c00;">
                    <li>✅ Multi-agent AI workflow</li>
                    <li>✅ Visual workflow diagrams</li>
                    <li>✅ Explainable AI results</li>
                    <li>✅ Performance metrics</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            # Resume preview section
            create_resume_preview_section()
            
            # Stats cards
            st.markdown("""
            <div class="stats-card">
                <h3>95%</h3>
                <p>Matching Accuracy</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="stats-card" style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);">
                <h3>10K+</h3>
                <p>Resumes Processed</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="stats-card" style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);">
                <h3>24/7</h3>
                <p>AI Availability</p>
            </div>
            """, unsafe_allow_html=True)

        # Enhanced usage tips
        with st.expander("💡 Pro Tips for Maximum Success", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🎯 For Resume Matching:**
                - Upload high-quality PDF resumes
                - Include complete job descriptions with requirements
                - Review missing skills for targeted improvements
                - Use semantic keywords from job postings
                - Check ATS compatibility scores
                """)
            
            with col2:
                st.markdown("""
                **📝 For Resume Building:**
                - Start with a compelling professional summary
                - Use action verbs and quantified achievements
                - Organize skills by relevant categories
                - Include professional photo for better impact
                - Tailor content for specific industries
                """)

        # Call to action
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); 
                    padding: 2rem; border-radius: 15px; text-align: center; margin: 2rem 0;
                    border: 2px solid #e0e7ff;">
            <h3 style="color: #667eea; margin-bottom: 1rem;">🚀 Ready to Transform Your Career?</h3>
            <p style="color: #666; margin-bottom: 1.5rem;">Join thousands of professionals who have enhanced their job search with our AI-powered tools.</p>
            <p style="color: #667eea; font-weight: 600;">👈 Choose your path from the sidebar to get started!</p>
        </div>
        """, unsafe_allow_html=True)

    # ----------------- RESUME MATCHING -----------------
    elif mode == "🎯 Resume Matching":
        # Header for Resume Matching
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); 
                    padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;">
            <h1>🎯 Smart Resume Matching</h1>
            <p>Analyze your resume against job descriptions with AI-powered insights</p>
        </div>
        """, unsafe_allow_html=True)

        # Main matching interface
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("""
            <div style="background: white; padding: 2rem; border-radius: 15px; 
                        box-shadow: 0 5px 20px rgba(0,0,0,0.08); margin-bottom: 1rem;
                        border-left: 5px solid #4CAF50;">
                <h3 style="color: #4CAF50; margin-bottom: 1rem;">📄 Upload Your Resume</h3>
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
            <div style="background: white; padding: 2rem; border-radius: 15px; 
                        box-shadow: 0 5px 20px rgba(0,0,0,0.08); margin-bottom: 1rem;
                        border-left: 5px solid #2196F3;">
                <h3 style="color: #2196F3; margin-bottom: 1rem;">📋 Job Description</h3>
            </div>
            """, unsafe_allow_html=True)
            
            job_desc = st.text_area(
                "Paste the complete job description", 
                height=200,
                placeholder="Paste the complete job description here including:\n• Job title and company\n• Required qualifications\n• Responsibilities\n• Preferred skills\n• Experience requirements",
                help="Include all sections of the job posting for comprehensive analysis"
            )

        # Analysis button
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
            # Progress indicator
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("🤖 Our AI agents are analyzing your resume..."):
                embed = EmbeddingService()
                steps = []

                # Step 1: Resume parsing
                status_text.text("📄 Parsing resume content...")
                progress_bar.progress(20)
                resume_bytes = resume_file.getvalue()
                a1 = resume_parser_agent(resume_bytes)
                steps.append(a1)

                # Step 2: Job parsing
                status_text.text("📋 Analyzing job description...")
                progress_bar.progress(40)
                a2 = job_parser_agent(job_desc)
                steps.append(a2)

                # Step 3: Content enhancement
                status_text.text("✨ Enhancing content analysis...")
                progress_bar.progress(60)
                a3 = content_enhancer_agent(a1.outputs["raw_text"])
                steps.append(a3)

                # Step 4: Matching and scoring
                status_text.text("🎯 Calculating match score and recommendations...")
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
                status_text.text("📊 Generating visual workflow...")
                progress_bar.progress(100)
                trace = build_workflow_trace(steps)
                fig = workflow_figure(trace)

                status_text.text("✅ Analysis complete!")
                
                # Clear progress indicators after a short delay
                import time
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()

            # Results section with enhanced styling
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f8fff8 0%, #e8f8e8 100%); 
                        padding: 2rem; border-radius: 15px; margin: 2rem 0;
                        border-left: 5px solid #4CAF50;">
                <h2 style="color: #2e7d32; margin-bottom: 1rem;">📊 Analysis Results</h2>
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
                <div style="background: linear-gradient(135deg, #cce7ff 0%, #b3d9ff 100%); 
                            padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem;">
                    <h4 style="color: #004085; margin-bottom: 0.5rem;">📋 Professional Analysis Report</h4>
                    <p style="color: #004085; margin: 0;">Get a detailed PDF report with all analysis results, recommendations, and action items.</p>
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
        <div style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); 
                    padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;">
            <h1>📝 Professional Resume Builder</h1>
            <p>Create stunning, ATS-friendly resumes with AI-powered assistance</p>
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
            <div style="background: white; padding: 2rem; border-radius: 15px; 
                        box-shadow: 0 5px 20px rgba(0,0,0,0.08); margin-bottom: 2rem;">
                <h2 style="color: #2196F3; margin-bottom: 1rem;">✏️ Resume Information</h2>
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
            # Preview section and tips
            create_resume_preview_section()
            
            # Resume tips
            st.markdown("""
            <div style="background: white; padding: 1.5rem; border-radius: 15px; 
                        box-shadow: 0 5px 20px rgba(0,0,0,0.08); margin-bottom: 1rem;">
                <h3 style="color: #FF9800; margin-bottom: 1rem;">💡 Quick Tips</h3>
                <ul style="color: #666; line-height: 1.6;">
                    <li><strong>Action Verbs:</strong> Start with Led, Developed, Increased</li>
                    <li><strong>Quantify:</strong> Include numbers and percentages</li>
                    <li><strong>Keywords:</strong> Match job description terms</li>
                    <li><strong>ATS-Friendly:</strong> Simple, clean formatting</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Industry stats
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c8 100%); 
                        padding: 1.5rem; border-radius: 15px; text-align: center; margin-bottom: 1rem;">
                <h4 style="color: #2e7d32; margin-bottom: 1rem;">📈 Resume Facts</h4>
                <p style="color: #2e7d32; margin: 0.5rem 0;"><strong>6 seconds</strong><br>Average recruiter review time</p>
                <p style="color: #2e7d32; margin: 0.5rem 0;"><strong>75%</strong><br>Resumes filtered by ATS</p>
                <p style="color: #2e7d32; margin: 0.5rem 0;"><strong>2 pages</strong><br>Optimal resume length</p>
            </div>
            """, unsafe_allow_html=True)

        # Generate Resume Button
        st.markdown("### 📄 Generate Your Professional Resume")
        
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
                    <div class="success-message" style="text-align: center; margin: 2rem 0;">
                        <h3>✅ Resume Generated Successfully!</h3>
                        <p>Your professional resume is ready for download.</p>
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
                    <div class="info-message" style="text-align: center; margin: 1rem 0;">
                        <p><strong>🎯 Your resume features:</strong></p>
                        <p>✓ Clean, professional formatting • ✓ ATS optimization • ✓ Modern design • ✓ Industry best practices</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Error generating resume: {str(e)}")
                    st.markdown("Please check your input data and try again.")

        # Enhanced tips section
        with st.expander("💡 Professional Resume Writing Guide", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **📝 Content Excellence:**
                - **Power Words**: Led, Developed, Implemented, Increased, Optimized
                - **Quantify Impact**: "Increased sales by 25%" vs "Increased sales"
                - **STAR Method**: Situation, Task, Action, Result framework
                - **Keywords**: Mirror language from target job descriptions
                - **Relevance**: Tailor content to specific roles and industries
                
                **🎯 ATS Optimization:**
                - Use standard section headings (Experience, Education, Skills)
                - Include relevant keywords naturally in context
                - Avoid images, tables, and complex formatting
                - Use common fonts (Arial, Calibri, Times New Roman)
                - Save as PDF to preserve formatting
                """)
            
            with col2:
                st.markdown("""
                **🎨 Visual Design:**
                - **Consistency**: Uniform formatting throughout document
                - **White Space**: Adequate margins and line spacing
                - **Hierarchy**: Clear distinction between sections and subsections
                - **Length**: 1-2 pages depending on experience level
                - **Professional**: Clean, modern appearance without distractions
                
                **✅ Final Checklist:**
                - Proofread for spelling and grammar errors
                - Verify all contact information is current
                - Ensure consistent date formatting
                - Check that all bullet points add value
                - Test PDF rendering on different devices
                """)


if __name__ == "__main__":
    main()