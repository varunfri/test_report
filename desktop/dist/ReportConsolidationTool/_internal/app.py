import streamlit as st
import pandas as pd
import yaml
import os
import plotly.express as px
from datetime import datetime
import json

# Import local services
from services.loader import FileLoader
from services.validator import DataValidator
from services.transformer import DataTransformer
from services.merger import DataMerger
from services.exporter import DataExporter
import importlib
import llm.column_mapper
importlib.reload(llm.column_mapper)
from llm.column_mapper import OllamaMapper
from services.logger import logger

# Caching connection check to prevent UI latency with slow or offline remote servers
@st.cache_data(ttl=15)
def cached_check_connection(host: str):
    mapper = OllamaMapper(host=host)
    return mapper.check_connection()

# Helper function to load Ollama session config safely across refreshes
def load_ollama_config() -> dict:
    config_file = "config/ollama_config.json"
    default_config = {
        "ollama_host": "http://localhost:11434",
        "use_ai": False,
        "selected_model": None
    }
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f) or default_config
        except Exception:
            return default_config
    return default_config

# Helper function to save Ollama session config
def save_ollama_config(host: str, use_ai: bool, model: str = None):
    config_file = "config/ollama_config.json"
    os.makedirs("config", exist_ok=True)
    try:
        with open(config_file, "w") as f:
            json.dump({
                "ollama_host": host,
                "use_ai": use_ai,
                "selected_model": model
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save Ollama config: {e}")


# Page layout & visual setup
st.set_page_config(
    page_title="NA, Blocked Report Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling via markdown
st.markdown("""
<style>
    .main-title {
        font-family: 'Segoe UI', sans-serif;
        color: #1E293B;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #64748B;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E293B;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to load configuration files safely
def load_yaml_config(file_path: str, default_data: dict) -> dict:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f) or default_data
        except Exception:
            return default_data
    return default_data

# Main application orchestrator
def main():
    # Header Section
    st.markdown('<div class="main-title">NA, Blocked Report Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Standardize, validate, and merge regional test execution reports using custom transformation rules and Ollama AI.</div>', unsafe_allow_html=True)

    # 1. Load Configurations
    default_mappings = {
        "column_mapping": {
            "Testcase ID": "Testcase ID",
            "Test_ID": "Testcase ID",
            "TC_ID": "Testcase ID",
            "Test Case": "Testcase ID",
            "Testcase Status": "Testcase Status",
            "Status": "Testcase Status",
            "Module": "Module",
            "Models": "Module",
            "Function": "Function",
            "Tester": "Tester",
            "Comment": "Comment"
        },
        "value_mapping": {
            "Testcase Status": {
                "N/A": "NA",
                "NA": "NA",
                "Not Applicable": "NA",
                "Blocked": "Blocked",
                "BLOCK": "Blocked",
                "Dependency": "Blocked"
            }
        }
    }
    default_filters = {
        "allowed_statuses": ["NA", "Blocked"]
    }

    mappings_config = load_yaml_config("config/mappings.yaml", default_mappings)
    filters_config = load_yaml_config("config/filters.yaml", default_filters)

    # Maintain column mappings and value mappings in session state
    if "col_mapping" not in st.session_state:
        st.session_state.col_mapping = mappings_config.get("column_mapping", {})
    if "val_mapping" not in st.session_state:
        st.session_state.val_mapping = mappings_config.get("value_mapping", {})
    if "allowed_statuses" not in st.session_state:
        st.session_state.allowed_statuses = filters_config.get("allowed_statuses", ["NA", "Blocked"])

    # 2. Sidebar Configuration Panel
    st.sidebar.header("Global Parameters")
    
    release_name = st.sidebar.text_input("Target Release", value="v1.0")
    execution_date = st.sidebar.date_input("Consolidation Date", value=datetime.today())
    execution_date_str = execution_date.strftime("%Y-%m-%d")

    keep_columns_mode = st.sidebar.checkbox(
        "Retain Original Columns",
        value=False,
        help="If checked, retains extra columns from source sheets alongside target schema columns."
    )

    # Load persisted Ollama parameters
    ollama_config = load_ollama_config()
    saved_host = ollama_config.get("ollama_host", "http://localhost:11434")
    saved_use_ai = ollama_config.get("use_ai", False)
    saved_model = ollama_config.get("selected_model", None)

    # Ollama AI Configuration
    st.sidebar.markdown("---")
    st.sidebar.header("Ollama AI Assistant")
    
    ollama_host = st.sidebar.text_input("Ollama Host URL", value=saved_host)
    
    # Initialize Ollama Mapper
    ollama_mapper = OllamaMapper(host=ollama_host)
    
    # Check Ollama connection status automatically (cached)
    is_connected, loaded_models = cached_check_connection(ollama_host)
    
    # Deduplicate models
    loaded_models = list(dict.fromkeys(loaded_models))
    
    default_model_index = 0
    if saved_model and saved_model in loaded_models:
        default_model_index = loaded_models.index(saved_model)
        
    if is_connected:
        st.sidebar.success("🟢 Ollama Connected")
        if loaded_models:
            selected_model = st.sidebar.selectbox(
                "Ollama Model", 
                options=loaded_models,
                index=default_model_index,
                help="Only models currently installed on your local Ollama system are shown."
            )
            use_ai = st.sidebar.toggle("Enable AI-Assisted Mapping", value=saved_use_ai)
        else:
            st.sidebar.warning("⚠️ No models found in your local Ollama system. Please install a model (e.g. running 'ollama pull llama3' in your terminal).")
            selected_model = None
            use_ai = False
    else:
        st.sidebar.error("🔴 Ollama Offline / Not Exposed")
        st.sidebar.info("Ollama is not running or is not exposed at the specified URL. Start Ollama locally or check your connection parameters.")
        selected_model = None
        use_ai = False

    # Save Ollama parameters if they changed
    if (ollama_host != saved_host or 
        use_ai != saved_use_ai or 
        selected_model != saved_model):
        save_ollama_config(ollama_host, use_ai, selected_model)

    # Sidebar Quick AI Query Widget
    if is_connected and "consolidated_data" in st.session_state and st.session_state.consolidated_data is not None and not st.session_state.consolidated_data.empty:
        st.sidebar.markdown("---")
        with st.sidebar.expander("💬 Quick AI Query", expanded=True):
            sidebar_q = st.sidebar.text_input(
                "Ask a quick question:",
                placeholder="e.g. Total blocked in CN?",
                key="sidebar_query_input"
            )
            if st.sidebar.button("Query AI", key="sidebar_query_button", use_container_width=True):
                if sidebar_q.strip():
                    with st.sidebar.spinner("Querying..."):
                        sidebar_ans = ollama_mapper.query_report(
                            df=st.session_state.consolidated_data,
                            question=sidebar_q.strip(),
                            model=selected_model
                        )
                        st.session_state.sidebar_chat_history = {
                            "question": sidebar_q.strip(),
                            "answer": sidebar_ans
                        }
                else:
                    st.sidebar.warning("Please enter a question.")
            
            if "sidebar_chat_history" in st.session_state:
                st.sidebar.markdown(f"**Q:** *{st.session_state.sidebar_chat_history['question']}*")
                st.sidebar.info(st.session_state.sidebar_chat_history['answer'])

    # Main Tabs
    tab_consolidator, tab_configs, tab_statistics, tab_assistant = st.tabs([
        "📁 File Consolidator", 
        "⚙️ Rule Configurations", 
        "📊 Pivot & Visual Metrics",
        "🤖 AI Report Assistant"
    ])

    # Tab 1: File Consolidator Dashboard
    with tab_consolidator:
        st.subheader("Upload Regional Excel Sheets")
        st.info("Upload Excel sheets from regional teams. Uploaded reports are saved in your workspace and will persist across page refreshes.")

        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)

        # Initialize key rotation in session state to programmatically clear the uploader widget on save
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

        uploaded_files = st.file_uploader(
            "Select new regional .xlsx reports to upload",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key=f"file_uploader_{st.session_state.uploader_key}"
        )

        # Save new files to persistent uploads/ directory
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(uploads_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.session_state.uploader_key += 1
            # Clear old processing state
            if "process_success" in st.session_state:
                del st.session_state.process_success
            if "consolidated_data" in st.session_state:
                del st.session_state.consolidated_data
            st.success("Reports uploaded and saved to workspace successfully.")
            st.rerun()

        # Load and scan saved reports from the persistent workspace folder
        saved_files = []
        if os.path.exists(uploads_dir):
            saved_files = sorted([f for f in os.listdir(uploads_dir) if f.endswith(('.xlsx', '.xls'))])

        file_meta = []
        if saved_files:
            st.markdown(f"**Saved Reports in Workspace:** {len(saved_files)}")
            
            # Button to clear all files
            if st.button("🗑️ Clear All Uploaded Reports"):
                for filename in saved_files:
                    try:
                        os.remove(os.path.join(uploads_dir, filename))
                    except Exception:
                        pass
                # Clear old processing state
                if "process_success" in st.session_state:
                    del st.session_state.process_success
                if "consolidated_data" in st.session_state:
                    del st.session_state.consolidated_data
                st.success("All reports removed.")
                st.rerun()
                
            st.markdown("### Regional Mapping Verification")
            
            for idx, filename in enumerate(saved_files):
                file_path = os.path.join(uploads_dir, filename)
                
                # Auto-detect region name from filename (e.g. US.xlsx -> US)
                base_name = os.path.splitext(filename)[0].upper()
                # Remove common suffixes like _report or _data
                auto_region = base_name.replace("_REPORT", "").replace("_DATA", "")
                
                # Fetch available sheets
                try:
                    sheets = FileLoader.get_sheet_names(file_path)
                except Exception as e:
                    st.error(f"Error reading file {filename}: {str(e)}")
                    continue
                
                with st.expander(f"📄 {filename}", expanded=True):
                    row_col1, row_col2, row_col3 = st.columns([3, 3, 1])
                    with row_col1:
                        region_val = st.text_input(
                            f"Region for {filename}", 
                            value=auto_region, 
                            key=f"reg_{idx}"
                        )
                    with row_col2:
                        sheet_val = st.selectbox(
                            f"Sheet name to read", 
                            options=sheets, 
                            index=0, 
                            key=f"sh_{idx}"
                        )
                    with row_col3:
                        st.write("") # padding
                        st.write("") # padding
                        if st.button("❌ Remove", key=f"rm_{idx}"):
                            try:
                                os.remove(file_path)
                                # Clear old processing state
                                if "process_success" in st.session_state:
                                    del st.session_state.process_success
                                if "consolidated_data" in st.session_state:
                                    del st.session_state.consolidated_data
                                st.success(f"Removed {filename}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to remove: {str(e)}")
                    
                    file_meta.append({
                        "file_obj": file_path,
                        "filename": filename,
                        "region": region_val,
                        "sheet": sheet_val
                    })

            # Run button
            st.markdown("---")
            if st.button("Process & Consolidate Files", type="primary"):
                logger.info(f"User clicked 'Process & Consolidate Files'. Total files to process: {len(file_meta)} (AI Enabled: {use_ai})")
                processed_dfs = []
                validation_results = []
                
                with st.spinner("Processing regional files..."):
                    for file_info in file_meta:
                        try:
                            logger.info(f"Starting processing for file: {file_info['filename']} (Region: {file_info['region']}, Sheet: {file_info['sheet']})")
                            # 1. Load Data
                            df_raw = FileLoader.load_sheet(
                                file_info["file_obj"], 
                                sheet_name=file_info["sheet"]
                            )
                            
                            # 2. Dynamic column mapping: AI or configuration-based
                            active_col_mappings = st.session_state.col_mapping.copy()
                            ai_applied = False
                            
                            if use_ai:
                                with st.status(f"AI scanning columns for {file_info['filename']}...", expanded=False):
                                    ai_mappings = ollama_mapper.get_column_mappings(
                                        source_cols=list(df_raw.columns),
                                        target_cols=["Testcase ID", "Testcase Status"],
                                        model=selected_model
                                    )
                                    if ai_mappings:
                                        # Merge AI suggested mappings with standard ones
                                        active_col_mappings.update(ai_mappings)
                                        ai_applied = True
                                        st.write("Suggested Mappings:", ai_mappings)
                            
                            # 3. Validate Sheet
                            validator = DataValidator(target_columns=["Testcase ID", "Testcase Status"])
                            val_report = validator.validate(
                                df=df_raw,
                                col_mapping=active_col_mappings,
                                allowed_statuses=set(st.session_state.allowed_statuses)
                            )
                            
                            # 4. If validation passed, apply transformation
                            if val_report["is_valid"]:
                                # Apply status mapping updates dynamically if AI is enabled and there are unknown statuses
                                active_val_mappings = st.session_state.val_mapping.copy()
                                
                                if use_ai and val_report["unknown_statuses"]:
                                    with st.status(f"AI resolving status values for {file_info['filename']}...", expanded=False):
                                        ai_val_mappings = ollama_mapper.get_status_mappings(
                                            raw_statuses=val_report["unknown_statuses"],
                                            standard_statuses=st.session_state.allowed_statuses,
                                            model=selected_model
                                        )
                                        if ai_val_mappings:
                                            active_val_mappings["Testcase Status"].update(ai_val_mappings)
                                            st.write("Status translation mappings:", ai_val_mappings)
                                
                                df_transformed = DataTransformer.transform(
                                    df=df_raw,
                                    col_mapping=active_col_mappings,
                                    value_mapping=active_val_mappings,
                                    allowed_statuses=set(st.session_state.allowed_statuses),
                                    region=file_info["region"],
                                    execution_date=execution_date_str,
                                    release=release_name,
                                    keep_all_columns=keep_columns_mode
                                )
                                processed_dfs.append(df_transformed)
                                logger.info(f"File {file_info['filename']} transformed successfully.")
                            else:
                                logger.error(f"File {file_info['filename']} failed validation: {val_report['errors']}")
                                
                            val_report["region"] = file_info["region"]
                            val_report["filename"] = file_info["filename"]
                            val_report["ai_applied"] = ai_applied
                            validation_results.append(val_report)
                            
                        except Exception as e:
                            logger.error(f"Critical processing failure on {file_info['filename']}: {str(e)}", exc_info=True)
                            st.error(f"Critical processing failure on {file_info['filename']}: {str(e)}")
                
                # Save validation results and processed dataframes to session state
                st.session_state.validation_results = validation_results
                if processed_dfs:
                    st.session_state.consolidated_data = DataMerger.merge(processed_dfs)
                    st.session_state.process_success = True
                    logger.info("Consolidation run finished successfully.")
                else:
                    st.session_state.consolidated_data = None
                    st.session_state.process_success = False
                    logger.warning("Consolidation run finished with no valid transformed records.")
                
                # Force rerun to transition to persistent display state
                st.rerun()

            # Persistent Rendering Section (Active on download clicks or subsequent interactions!)
            if "process_success" in st.session_state:
                validation_results = st.session_state.validation_results
                
                # Render validation reports
                st.markdown("### Process Summaries")
                
                has_any_errors = False
                for val_rep in validation_results:
                    status_emoji = "✅" if val_rep["is_valid"] else "❌"
                    status_text = "Passed Validation" if val_rep["is_valid"] else "Failed Validation"
                    ai_badge = " 🤖 AI Enabled" if val_rep.get("ai_applied") else ""
                    
                    with st.expander(f"{status_emoji} Region: {val_rep['region']} | {val_rep['filename']} ({status_text}){ai_badge}"):
                        st.markdown(f"**Rows loaded:** {val_rep['row_count']}")
                        if val_rep["errors"]:
                            has_any_errors = True
                            st.error("Errors:")
                            for err in val_rep["errors"]:
                                st.write(f"- {err}")
                        if val_rep["warnings"]:
                            st.warning("Warnings:")
                            for warn in val_rep["warnings"]:
                                st.write(f"- {warn}")
                        if val_rep.get("unknown_statuses"):
                            st.info(f"Raw unmapped statuses: {', '.join(val_rep['unknown_statuses'])}")
                
                # Render consolidation UI if successful
                if st.session_state.process_success and st.session_state.consolidated_data is not None:
                    consolidated_df = st.session_state.consolidated_data
                    
                    st.markdown("---")
                    st.success(f"Successfully consolidated your regional reports.")
                    
                    # Metrics cards
                    card1, card2, card3 = st.columns(3)
                    with card1:
                        st.markdown(
                            f'<div class="metric-card"><div class="metric-value">{len(consolidated_df)}</div><div class="metric-label">Total Blocked/NA Records</div></div>', 
                            unsafe_allow_html=True
                        )
                    with card2:
                        na_count = len(consolidated_df[consolidated_df["Testcase Status"] == "NA"])
                        st.markdown(
                            f'<div class="metric-card"><div class="metric-value">{na_count}</div><div class="metric-label">NA Test Cases</div></div>', 
                            unsafe_allow_html=True
                        )
                    with card3:
                        blocked_count = len(consolidated_df[consolidated_df["Testcase Status"] == "Blocked"])
                        st.markdown(
                            f'<div class="metric-card"><div class="metric-value">{blocked_count}</div><div class="metric-label">Blocked Test Cases</div></div>', 
                            unsafe_allow_html=True
                        )
                    
                    # Preview
                    st.markdown("### Consolidated Data Preview")
                    st.dataframe(consolidated_df.head(100), use_container_width=True)
                    
                    # Download Excel
                    try:
                        excel_data = DataExporter.export_to_excel(consolidated_df)
                        st.download_button(
                            label="📥 Download Consolidated Excel Report",
                            data=excel_data,
                            file_name="Final_Report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # Confluence Collaboration Export Section
                        st.markdown("---")
                        st.markdown("### 📋 Confluence Collaboration Export")
                        st.info("Copy the generated Confluence macros or download files to paste directly into your Confluence page.")
                        
                        from services.confluence import ConfluenceGenerator
                        xml_markup = ConfluenceGenerator.generate_confluence_xml(consolidated_df)
                        html_markup = ConfluenceGenerator.generate_pure_html(consolidated_df)
                        
                        conf_col1, conf_col2 = st.columns(2)
                        with conf_col1:
                            st.download_button(
                                label="💾 Download Confluence Storage XML",
                                data=xml_markup,
                                file_name="Confluence_Storage_Format.xml",
                                mime="text/xml"
                            )
                        with conf_col2:
                            st.download_button(
                                label="🌐 Download HTML Fallback Layout",
                                data=html_markup,
                                file_name="Confluence_HTML_Fallback.html",
                                mime="text/html"
                            )
                            
                        # Show raw copyable code block in an expander
                        with st.expander("🔍 Preview & Copy Confluence XML (Storage Format)"):
                            st.code(xml_markup, language="xml")
                            
                        with st.expander("🔍 Preview & Copy HTML Fallback (details/summary)"):
                            st.code(html_markup, language="html")
                            
                    except Exception as e:
                        st.error(f"Failed to generate download packages: {str(e)}")
                else:
                    st.error("No data consolidated. Ensure target Excel structures are corrected and try again.")

        else:
            st.warning("Please upload one or more Excel reports to start.")

    # Tab 2: Configurations and Mappings Rules Panel
    with tab_configs:
        st.subheader("Predefined Standardization Rules")
        st.write("Manage active column mappings and allowed status values. These values are synced from configuration files.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Active Header Mappings")
            st.write("Maps regional source headers to standardized target fields.")
            
            # Render a nice table of source columns
            map_data = []
            for src, tgt in st.session_state.col_mapping.items():
                map_data.append({"Source Header": src, "Target Standard Header": tgt})
            
            mapping_df = pd.DataFrame(map_data)
            st.dataframe(mapping_df, use_container_width=True, hide_index=True)
            
            # Interactive add mapping
            with st.form("add_header_mapping_form"):
                new_src = st.text_input("Raw Source Header Name (e.g. TC_Num)")
                new_tgt = st.selectbox("Standard Target Mapping", options=["Testcase ID", "Testcase Status", "Module", "Function", "Tester", "Comment"])
                submit_map = st.form_submit_button("Add Mapping Rule")
                if submit_map and new_src:
                    st.session_state.col_mapping[new_src.strip()] = new_tgt
                    st.success(f"Added mapping: {new_src} -> {new_tgt}")
                    st.rerun()

        with col2:
            st.markdown("### Allowed Status Standardizations")
            st.write("Maps variations of status strings to defined targets.")
            
            status_vals = []
            for src, tgt in st.session_state.val_mapping.get("Testcase Status", {}).items():
                status_vals.append({"Raw Value": src, "Standard Value": tgt})
            
            status_df = pd.DataFrame(status_vals)
            st.dataframe(status_df, use_container_width=True, hide_index=True)
            
            # Interactive add status mapping
            with st.form("add_status_mapping_form"):
                new_raw = st.text_input("Raw Status String (e.g. BLOKED)")
                new_std = st.selectbox("Standard Status", options=st.session_state.allowed_statuses)
                submit_val = st.form_submit_button("Add Status Standard")
                if submit_val and new_raw:
                    if "Testcase Status" not in st.session_state.val_mapping:
                        st.session_state.val_mapping["Testcase Status"] = {}
                    st.session_state.val_mapping["Testcase Status"][new_raw.strip()] = new_std
                    st.success(f"Added mapping: {new_raw} -> {new_std}")
                    st.rerun()

    # Tab 3: Interactive Statistics & Visual Charts
    with tab_statistics:
        st.subheader("Statistical pivot table and regional metrics")
        
        if "consolidated_data" in st.session_state and not st.session_state.consolidated_data.empty:
            consolidated_df = st.session_state.consolidated_data
            
            pivot_stats = DataExporter.generate_pivot_statistics(consolidated_df)
            
            col_stat1, col_stat2 = st.columns([2, 3])
            
            with col_stat1:
                st.markdown("### Pivot Table")
                st.dataframe(pivot_stats, use_container_width=True, hide_index=True)
            
            with col_stat2:
                st.markdown("### Status Counts per Region")
                # Filter out the total row from pivot table for representation in chart
                chart_df = consolidated_df.groupby(["Region", "Testcase Status"]).size().reset_index(name="Count")
                
                fig = px.bar(
                    chart_df,
                    x="Region",
                    y="Count",
                    color="Testcase Status",
                    barmode="group",
                    color_discrete_map={"Blocked": "#EF4444", "NA": "#3B82F6"},
                    labels={"Count": "Test Case Count"},
                    template="plotly_white"
                )
                fig.update_layout(
                    font_family="Segoe UI",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
        else:
            st.warning("Please upload and process files in the File Consolidator tab first to view statistics.")

    # Tab 4: AI Report Assistant
    with tab_assistant:
        st.subheader("🤖 AI Report Assistant")
        st.write("Query and analyze your consolidated test report using natural language. Ask questions about blockers, testers, modules, or regional trends.")
        
        if "consolidated_data" not in st.session_state or st.session_state.consolidated_data is None or st.session_state.consolidated_data.empty:
            st.info("💡 Please upload and process regional reports in the **File Consolidator** tab to enable the AI Report Assistant.")
        elif not is_connected:
            st.error("🔴 Ollama Offline / Not Exposed")
            st.info("Start your local Ollama server to enable conversational analysis over your consolidated reports.")
        else:
            # Initialize conversation state
            if "assistant_chat_history" not in st.session_state:
                st.session_state.assistant_chat_history = []
                
            # Helper Quick Questions
            st.markdown("##### 💡 Quick Queries")
            quick_cols = st.columns(3)
            q1 = "Summarize the primary blockers across all regions."
            q2 = "Which modules have the highest number of Blocked cases?"
            q3 = "Identify which testers are assigned to NA cases and where."
            
            clicked_q = None
            if quick_cols[0].button(q1, use_container_width=True):
                clicked_q = q1
            if quick_cols[1].button(q2, use_container_width=True):
                clicked_q = q2
            if quick_cols[2].button(q3, use_container_width=True):
                clicked_q = q3
                
            # Input Text Box
            st.markdown("##### 💬 Custom Query")
            custom_q = st.text_input(
                "Enter your question here:",
                placeholder="e.g. List all testcases in the US region that are Blocked.",
                key="assistant_custom_query_input"
            )
            
            col_btn_clear, col_btn_ask = st.columns([1, 4])
            
            if col_btn_clear.button("Clear Chat", use_container_width=True):
                st.session_state.assistant_chat_history = []
                st.rerun()
                
            ask_clicked = col_btn_ask.button("Ask AI Assistant", type="primary", use_container_width=True)
            
            # Resolve active question
            active_q = clicked_q or (custom_q.strip() if ask_clicked and custom_q.strip() else None)
            
            if active_q:
                with st.spinner("AI Assistant is analyzing the consolidated report..."):
                    answer = ollama_mapper.query_report(
                        df=st.session_state.consolidated_data,
                        question=active_q,
                        model=selected_model
                    )
                    # Append to history
                    st.session_state.assistant_chat_history.append({
                        "question": active_q,
                        "answer": answer,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    st.rerun()
                    
            # Display conversation history
            if st.session_state.assistant_chat_history:
                st.markdown("---")
                st.markdown("##### 💬 Conversation History")
                for i, item in enumerate(reversed(st.session_state.assistant_chat_history)):
                    st.markdown(f"**👤 Question [{item['timestamp']}]:** {item['question']}")
                    st.info(item["answer"])
                    st.markdown("---")

if __name__ == "__main__":
    main()
