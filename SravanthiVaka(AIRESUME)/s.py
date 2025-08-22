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


st.set_page_config(page_title="AI Resume Matcher", layout="wide")

try:
    import importlib
    _dotenv = importlib.import_module("dotenv")
    # Load .env if present; do not override existing env vars
    _dotenv.load_dotenv(override=False)
except Exception:
    pass


def process_uploaded_image(uploaded_file) -> str:
    """Convert uploaded image to base64 data URL"""
    if uploaded_file is not None:
        try:
            # Open and resize image
            image = Image.open(uploaded_file)
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to reasonable size (max 300x300)
            image.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            img_data = buffer.getvalue()
            
            # Create data URL
            b64_string = base64.b64encode(img_data).decode()
            return f"data:image/jpeg;base64,{b64_string}"
        except Exception as e:
            st.error(f"Error processing image: {e}")
            return ""
    return ""


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
    
    # Update session state
    st.session_state[f"{key}_items"] = [item for item in st.session_state[f"{key}_items"] if True]  # Keep all for now
    
    return items


def dynamic_experience_input() -> List[Dict[str, Any]]:
    """Create dynamic experience section input"""
    if "experience_items" not in st.session_state:
        st.session_state["experience_items"] = [{}]
    
    experiences = []
    
    for i, exp in enumerate(st.session_state["experience_items"]):
        st.markdown(f"**Experience {i+1}**")
        
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
        st.markdown(f"**Education {i+1}**")
        
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
        st.markdown(f"**Project {i+1}**")
        
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
    # Sidebar navigation
    st.sidebar.title("Navigation")
    mode = st.sidebar.radio("Go to", ["Welcome", "Resume Matching", "Resume Builder"])

    # ----------------- WELCOME PAGE -----------------
    if mode == "Welcome":
        st.title("✨ AI-Powered Resume Builder with Job Matching ✨")
        st.caption("Multi-agent workflow · Semantic matching · Explainable results")

        st.markdown("""
        ### 👋 Welcome!
        This app helps you:
        - 📂 Upload your resume and match it to a job description
        - 🎯 Get a match score, missing skills, and recommendations
        - 📝 Build an ATS-friendly resume quickly with modern formatting

        ### ✨ New Features:
        - 🖼️ **Photo Upload**: Add a professional headshot to your resume
        - 📋 **Dynamic Sections**: Add multiple experiences, education, projects, and certifications
        - 🎨 **Modern Design**: Clean, single-column layout optimized for ATS systems
        - 📊 **Categorized Skills**: Organize skills by category (e.g., "Programming: Python, Java")

        👉 Use the **sidebar** to switch between features.
        """)

        # Add some usage tips
        with st.expander("💡 Pro Tips for Better Results"):
            st.markdown("""
            **For Resume Matching:**
            - Use a PDF resume for best text extraction
            - Paste the complete job description including requirements
            - Review missing skills to tailor your resume

            **For Resume Builder:**
            - Start with contact info and summary
            - Use action verbs in experience bullets
            - Quantify achievements when possible
            - Organize skills by category for better readability
            """)

    # ----------------- RESUME MATCHING -----------------
    elif mode == "Resume Matching":
        st.header("📂 Resume Matching")
        st.caption("Upload your resume and compare it to a job description for insights and recommendations")

        left, right = st.columns(2)

        with left:
            resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], accept_multiple_files=False)
            if resume_file is not None:
                st.success(f"✅ Loaded file: {resume_file.name}")

        with right:
            job_desc = st.text_area("Paste Job Description", height=300,
                                    placeholder="Paste the complete job description here including requirements, qualifications, and responsibilities...")

        run = st.button("🔍 Analyze Match", type="primary", use_container_width=True,
                        disabled=not (resume_file and job_desc))

        if run and resume_file and job_desc:
            with st.spinner("Analyzing your resume and job match..."):
                embed = EmbeddingService()
                steps = []

                resume_bytes = resume_file.getvalue()
                a1 = resume_parser_agent(resume_bytes)
                steps.append(a1)

                a2 = job_parser_agent(job_desc)
                steps.append(a2)

                a3 = content_enhancer_agent(a1.outputs["raw_text"])
                steps.append(a3)

                a4 = matcher_and_scoring_agent(
                    resume_text=a1.outputs["raw_text"],
                    job_text=job_desc,
                    resume_skills=a1.outputs["skills"],
                    job_skills=a2.outputs["skills"],
                    embedding_service=embed,
                )
                steps.append(a4)

                trace = build_workflow_trace(steps)
                fig = workflow_figure(trace)

                show_workflow_diagram(fig)

                show_match_summary(
                    score=float(a4.outputs["score"]),
                    confidence=float(a4.outputs["confidence"]),
                    missing_skills=list(a4.outputs["missing_skills"]),
                    explanation=str(a4.outputs["explanation"]),
                    top_snippets=list(a4.outputs["top_snippets"]),
                )

                show_agent_outputs([(s.name, s.outputs) for s in steps])

                with st.expander("📄 Download Detailed Report", expanded=True):
                    candidate = a1.outputs.get("name") or "Candidate"
                    pdf_bytes = generate_pdf_report(
                        candidate_name=candidate,
                        match_score=float(a4.outputs["score"]),
                        confidence=float(a4.outputs["confidence"]),
                        explanation=str(a4.outputs["explanation"]),
                        missing_skills=list(a4.outputs["missing_skills"]),
                        top_snippets=list(a4.outputs["top_snippets"]),
                    )
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"{candidate.replace(' ', '_').lower()}_match_report.pdf",
                        mime="application/pdf",
                    )

    # ----------------- RESUME BUILDER -----------------
    elif mode == "Resume Builder":
        st.header("📝 Professional Resume Builder")
        st.caption("Create a modern, ATS-friendly resume with clean formatting and professional design")

        # Initialize session state for dynamic inputs
        if "form_submitted" not in st.session_state:
            st.session_state.form_submitted = False

        # Resume form
        st.markdown("### ✏️ Fill Your Information")
        
        data: Dict[str, Any] = {}

        # Contact Information
        with st.expander("👤 Contact Information", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email Address", placeholder="john.doe@email.com")
            with col2:
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
                # Show preview
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.image(photo_file, caption="Preview", width=100)
                with col2:
                    st.success("✅ Photo uploaded")
                
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
                # Split by lines first, then by commas if no colons found
                lines = [line.strip() for line in skills_text.split('\n') if line.strip()]
                for line in lines:
                    if ':' in line:
                        skills.append(line)  # Keep categorized format
                    else:
                        # Split by comma and add individually
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

        # Generate Resume Button
        st.markdown("### 📄 Generate Your Resume")
        generate_button = st.button("🚀 Generate Professional Resume", type="primary", use_container_width=True)

        if generate_button:
            # Validate required fields
            if not data.get("name"):
                st.error("⚠️ Please enter your full name to generate the resume.")
                return
            
            with st.spinner("Creating your professional resume..."):
                try:
                    resume_pdf = generate_ats_resume_pdf(data)
                    dl_name = (data.get("name", "resume")).replace(" ", "_").lower() + "_professional_resume.pdf"
                    
                    st.success("✅ Resume generated successfully!")
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Your Resume",
                        data=resume_pdf,
                        file_name=dl_name,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    # Show preview message
                    st.info("💡 Your resume has been generated with a clean, professional format optimized for ATS systems. Download the PDF to view the final result.")
                    
                except Exception as e:
                    st.error(f"❌ Error generating resume: {str(e)}")
                    st.markdown("Please check your input data and try again.")

        # Tips section
        with st.expander("💡 Resume Writing Tips"):
            st.markdown("""
            **Content Tips:**
            - **Use action verbs**: Start bullet points with strong action words (Led, Developed, Implemented, Increased)
            - **Quantify achievements**: Include numbers, percentages, and specific results
            - **Tailor to the job**: Highlight relevant skills and experiences for your target role
            - **Keep it concise**: Aim for 1-2 pages depending on your experience level
            
            **Formatting Tips:**
            - **Consistency**: Use consistent formatting throughout
            - **White space**: Leave adequate margins and spacing for readability
            - **Keywords**: Include industry-specific keywords for ATS optimization
            - **Professional email**: Use a professional email address
            
            **ATS Optimization:**
            - **Simple formatting**: Avoid complex layouts, tables, and graphics
            - **Standard sections**: Use common section headings like "Experience", "Education"
            - **Keywords**: Mirror language from job descriptions
            - **File format**: PDF maintains formatting across different systems
            """)


if __name__ == "__main__":
    main()