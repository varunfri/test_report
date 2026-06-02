import sys
import os
import time
import socket
import threading
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import yaml
import json
import logging
from datetime import datetime

# Resolve application paths for both dev execution and packaged PyInstaller mode
base_path = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    root_path = sys._MEIPASS
else:
    root_path = os.path.abspath(os.path.join(base_path, ".."))

# Add root path to sys.path to import processing services
if root_path not in sys.path:
    sys.path.append(root_path)

from services.loader import FileLoader
from services.validator import DataValidator
from services.transformer import DataTransformer
from services.merger import DataMerger
from services.exporter import DataExporter
from services.confluence import ConfluenceGenerator
from services.logger import logger
from llm.column_mapper import OllamaMapper

# Custom Tkinter logging handler to redirect application logs to GUI console
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert('end', msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see('end')
        self.text_widget.after(0, append)

class DesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NA, Blocked Report Generator - Offline Desktop Client")
        self.root.geometry("1150x800")
        self.root.minsize(1000, 700)
        
        # Define Paths
        if getattr(sys, 'frozen', False):
            # Resolve executable directory containing the app bundle or binary
            exec_path = sys.executable
            # If macOS app bundle, go up 3 levels to exit ReportConsolidationTool.app/Contents/MacOS/ReportConsolidationTool
            if sys.platform == 'darwin' and '.app/Contents/MacOS/' in exec_path:
                exec_dir = os.path.abspath(os.path.join(os.path.dirname(exec_path), "..", "..", ".."))
            else:
                exec_dir = os.path.dirname(exec_path)
            
            # Persistent config directory inside the app's folder
            self.config_dir = os.path.join(exec_dir, "config")
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Copy default templates from sys._MEIPASS if they don't exist in the persistent config folder
            default_config_src = os.path.join(sys._MEIPASS, "config")
            for filename in ["mappings.yaml", "filters.yaml", "ollama_config.json"]:
                src_file = os.path.join(default_config_src, filename)
                dest_file = os.path.join(self.config_dir, filename)
                if not os.path.exists(dest_file) and os.path.exists(src_file):
                    try:
                        shutil.copy2(src_file, dest_file)
                    except Exception as e:
                        print(f"Error copying default config {filename}: {e}")
        else:
            self.config_dir = os.path.join(root_path, "config")
            
        self.mappings_path = os.path.join(self.config_dir, "mappings.yaml")
        self.filters_path = os.path.join(self.config_dir, "filters.yaml")
        self.ollama_config_path = os.path.join(self.config_dir, "ollama_config.json")
        
        # Load Configurations
        self.load_configurations()
        
        # Initialize States
        self.selected_files = []
        self.consolidated_df = None
        self.ollama_mapper = None
        
        # Apply Styling Themes
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.apply_theme_styles()
        
        # Create Layout
        self.create_layout()
        
        # Connect log handler to text area
        self.connect_log_handler()
        
        # Auto check Ollama on background thread
        threading.Thread(target=self.init_ollama_engine, daemon=True).start()

    def load_configurations(self):
        # Default configs
        self.default_mappings = {
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
        self.default_filters = {"allowed_statuses": ["NA", "Blocked"]}
        self.default_ollama = {
            "ollama_host": "http://localhost:11434",
            "use_ai": False,
            "selected_model": None
        }
        
        # Load YAML mappings
        if os.path.exists(self.mappings_path):
            try:
                with open(self.mappings_path, "r") as f:
                    self.mappings = yaml.safe_load(f) or self.default_mappings
            except Exception:
                self.mappings = self.default_mappings
        else:
            self.mappings = self.default_mappings

        # Load YAML filters
        if os.path.exists(self.filters_path):
            try:
                with open(self.filters_path, "r") as f:
                    self.filters = yaml.safe_load(f) or self.default_filters
            except Exception:
                self.filters = self.default_filters
        else:
            self.filters = self.default_filters
            
        # Load Ollama Config
        if os.path.exists(self.ollama_config_path):
            try:
                with open(self.ollama_config_path, "r") as f:
                    self.ollama_config = json.load(f) or self.default_ollama
            except Exception:
                self.ollama_config = self.default_ollama
        else:
            self.ollama_config = self.default_ollama

    def save_mappings_config(self):
        try:
            os.makedirs(os.path.dirname(self.mappings_path), exist_ok=True)
            with open(self.mappings_path, "w") as f:
                yaml.safe_dump(self.mappings, f, default_flow_style=False)
            logger.info("Saved column and status mappings configuration successfully.")
        except Exception as e:
            logger.error(f"Failed to save mappings configuration: {e}")

    def save_ollama_config(self):
        try:
            os.makedirs(os.path.dirname(self.ollama_config_path), exist_ok=True)
            with open(self.ollama_config_path, "w") as f:
                json.dump(self.ollama_config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save Ollama session config: {e}")

    def apply_theme_styles(self):
        # Configure slate-grey and dark-blue dashboard styling
        self.style.configure('.', font=('Segoe UI', 10), background='#F8FAFC', foreground='#0F172A')
        self.style.configure('TFrame', background='#F8FAFC')
        self.style.configure('TLabel', background='#F8FAFC', foreground='#334155')
        self.style.configure('Header.TLabel', font=('Segoe UI', 13, 'bold'), foreground='#0F172A')
        self.style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'), foreground='#1E293B', background='#F8FAFC')
        self.style.configure('Card.TFrame', background='#FFFFFF', relief='solid', borderwidth=1)
        self.style.configure('CardHeader.TFrame', background='#1E293B')
        self.style.configure('CardTitle.TLabel', background='#1E293B', foreground='#FFFFFF', font=('Segoe UI', 11, 'bold'))
        
        # Primary Action Buttons
        self.style.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'), background='#2563EB', foreground='#FFFFFF')
        self.style.map('Primary.TButton', background=[('active', '#1D4ED8')])
        
        # Normal Buttons
        self.style.configure('TButton', font=('Segoe UI', 10), background='#E2E8F0', foreground='#0F172A')
        self.style.map('TButton', background=[('active', '#CBD5E1')])
        
        # Tabs Style
        self.style.configure('TNotebook', background='#E2E8F0', padding=2)
        self.style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=(15, 6), background='#E2E8F0', foreground='#475569')
        self.style.map('TNotebook.Tab', background=[('selected', '#FFFFFF')], foreground=[('selected', '#1E293B')])

    def create_layout(self):
        # 1. Header panel
        header_frame = ttk.Frame(self.root, padding=(20, 15, 20, 10))
        header_frame.pack(fill='x')
        
        title_label = ttk.Label(header_frame, text="NA, Blocked Report Generator", style="Title.TLabel")
        title_label.pack(side='left')
        
        version_label = ttk.Label(header_frame, text="v1.0 (Offline Standalone)", font=('Segoe UI', 9, 'italic'), foreground='#64748B')
        version_label.pack(side='left', padx=15, pady=8)
        
        # 2. Main Tabbed Layout
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Initialize Tabs
        self.tab_consolidator = ttk.Frame(self.notebook, padding=15)
        self.tab_mappings = ttk.Frame(self.notebook, padding=15)
        self.tab_ai = ttk.Frame(self.notebook, padding=15)
        self.tab_logs = ttk.Frame(self.notebook, padding=15)
        
        self.notebook.add(self.tab_consolidator, text="📂 File Consolidator")
        self.notebook.add(self.tab_mappings, text="⚙️ Standard Mappings")
        self.notebook.add(self.tab_ai, text="🤖 Local AI Assistant")
        self.notebook.add(self.tab_logs, text="📜 Logs Console")
        
        # Build specific layouts
        self.build_consolidator_tab()
        self.build_mappings_tab()
        self.build_ai_tab()
        self.build_logs_tab()

    # --- TAB 1: FILE CONSOLIDATOR ---
    def build_consolidator_tab(self):
        # Left Panel - File Manager
        left_frame = ttk.Frame(self.tab_consolidator)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        file_list_header = ttk.Label(left_frame, text="Select Excel Files to Consolidate:", font=('Segoe UI', 11, 'bold'))
        file_list_header.pack(anchor='w', pady=(0, 5))
        
        # Scrollable file listbox
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True)
        
        self.file_listbox = tk.Listbox(list_frame, font=('Segoe UI', 10), selectmode='extended', relief='solid', borderwidth=1)
        self.file_listbox.pack(side='left', fill='both', expand=True)
        
        list_scroll = ttk.Scrollbar(list_frame, orient='vertical', command=self.file_listbox.yview)
        list_scroll.pack(side='right', fill='y')
        self.file_listbox.config(yscrollcommand=list_scroll.set)
        
        # File Action Buttons
        btn_frame = ttk.Frame(left_frame, padding=(0, 10, 0, 0))
        btn_frame.pack(fill='x')
        
        add_btn = ttk.Button(btn_frame, text="➕ Add Excel Files", command=self.action_add_files)
        add_btn.pack(side='left', padx=(0, 10))
        
        remove_btn = ttk.Button(btn_frame, text="❌ Remove Selected", command=self.action_remove_files)
        remove_btn.pack(side='left', padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="🗑️ Clear All", command=self.action_clear_files)
        clear_btn.pack(side='left', padx=5)

        # Right Panel - Configuration and Control Panel
        right_frame = ttk.Frame(self.tab_consolidator, width=380, padding=(10, 0, 0, 0))
        right_frame.pack(side='right', fill='both')
        right_frame.pack_propagate(False)
        
        # Metadata Frame
        meta_card = ttk.LabelFrame(right_frame, text="Report Parameters", padding=15)
        meta_card.pack(fill='x', pady=(0, 15))
        
        ttk.Label(meta_card, text="Release Version:").pack(anchor='w', pady=(0, 2))
        self.entry_release = ttk.Entry(meta_card)
        self.entry_release.insert(0, "v1.0")
        self.entry_release.pack(fill='x', pady=(0, 10))
        
        ttk.Label(meta_card, text="Execution Date (YYYY-MM-DD):").pack(anchor='w', pady=(0, 2))
        self.entry_date = ttk.Entry(meta_card)
        self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.entry_date.pack(fill='x')
        
        # Execution Card
        exec_card = ttk.LabelFrame(right_frame, text="Execution Actions", padding=15)
        exec_card.pack(fill='both', expand=True)
        
        self.status_label = ttk.Label(exec_card, text="Status: Ready", font=('Segoe UI', 10, 'bold'), foreground='#475569')
        self.status_label.pack(anchor='w', pady=(0, 15))
        
        self.run_btn = ttk.Button(exec_card, text="⚙️ Run Consolidation Pipeline", style="Primary.TButton", command=self.action_run_pipeline)
        self.run_btn.pack(fill='x', ipady=6, pady=(0, 10))
        
        self.export_btn = ttk.Button(exec_card, text="💾 Save Output Excel Workbook", command=self.action_save_excel, state='disabled')
        self.export_btn.pack(fill='x', ipady=4, pady=(0, 10))
        
        self.confluence_btn = ttk.Button(exec_card, text="📄 Generate Confluence Markup", command=self.action_generate_confluence, state='disabled')
        self.confluence_btn.pack(fill='x', ipady=4)
        
        # Summary Area
        self.summary_text = tk.Text(exec_card, height=10, font=('Consolas', 9), relief='solid', borderwidth=1, state='disabled')
        self.summary_text.pack(fill='both', expand=True, pady=(15, 0))

    def action_add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Regional Excel Reports",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        for path in paths:
            if path not in self.selected_files:
                self.selected_files.append(path)
                self.file_listbox.insert('end', os.path.basename(path))
        logger.info(f"Added {len(paths)} files to list. Total selected: {len(self.selected_files)}")

    def action_remove_files(self):
        selected_indices = list(self.file_listbox.curselection())
        # Delete from listbox and internal tracking in reverse order
        for idx in sorted(selected_indices, reverse=True):
            self.file_listbox.delete(idx)
            del self.selected_files[idx]
        logger.info(f"Removed selected files. Total files left: {len(self.selected_files)}")

    def action_clear_files(self):
        self.file_listbox.delete(0, 'end')
        self.selected_files.clear()
        logger.info("Cleared all files from selection list.")

    def action_run_pipeline(self):
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please add at least one regional Excel report to process.")
            return
            
        self.status_label.configure(text="Processing...", foreground="#D97706")
        self.run_btn.configure(state='disabled')
        self.export_btn.configure(state='disabled')
        self.confluence_btn.configure(state='disabled')
        self.summary_text.configure(state='normal')
        self.summary_text.delete('1.0', 'end')
        self.summary_text.insert('end', "Initializing Consolidation Pipeline...\n")
        self.summary_text.configure(state='disabled')
        
        # Run processing on a background thread to keep UI alive
        threading.Thread(target=self.process_pipeline_thread, daemon=True).start()

    def process_pipeline_thread(self):
        release = self.entry_release.get().strip() or "v1.0"
        exec_date = self.entry_date.get().strip() or datetime.now().strftime("%Y-%m-%d")
        
        col_mapping = self.mappings["column_mapping"]
        value_mapping = self.mappings["value_mapping"]
        allowed_statuses = set(self.filters["allowed_statuses"])
        
        processed_dfs = []
        pipeline_log = []
        validation_warnings = []
        
        for path in self.selected_files:
            filename = os.path.basename(path)
            pipeline_log.append(f"\nProcessing: {filename}")
            
            # 1. Load Data
            try:
                df = FileLoader.load_sheet(path)
                pipeline_log.append(f"  - Loaded {len(df)} rows. Columns found: {len(df.columns)}")
            except Exception as e:
                pipeline_log.append(f"  - Error loading file: {e}")
                logger.error(f"Error loading sheet {filename}: {e}")
                continue
                
            # Determine region
            region = "UNKNOWN"
            if ".AUS" in filename or "us_" in filename.lower():
                region = "US"
            elif ".AWZ" in filename or "cn_" in filename.lower():
                region = "CN"
            elif ".AEU" in filename or "eu_" in filename.lower():
                region = "EU"
            elif ".AJL" in filename or "jp_" in filename.lower():
                region = "JP"
                
            pipeline_log.append(f"  - Associated Region: {region}")
            
            # 2. Validate
            validator = DataValidator(target_columns=["Testcase ID", "Testcase Status"])
            report = validator.validate(df, col_mapping, allowed_statuses)
            
            if report["warnings"]:
                for warn in report["warnings"]:
                    validation_warnings.append(f"[{filename}] {warn}")
            
            if not report["is_valid"]:
                pipeline_log.append(f"  - VALIDATION ERROR: Skipping file. Missing: {report['missing_expected_columns']}")
                continue
                
            # 3. Transform
            try:
                df_trans = DataTransformer.transform(
                    df=df,
                    col_mapping=col_mapping,
                    value_mapping=value_mapping,
                    allowed_statuses=allowed_statuses,
                    region=region,
                    execution_date=exec_date,
                    release=release,
                    keep_all_columns=False
                )
                pipeline_log.append(f"  - Successfully transformed to {len(df_trans)} valid rows.")
                processed_dfs.append(df_trans)
            except Exception as e:
                pipeline_log.append(f"  - Error during transformation: {e}")
                logger.error(f"Error transforming {filename}: {e}")
                
        # 4. Merge
        if processed_dfs:
            pipeline_log.append("\nMerging all regional reports...")
            self.consolidated_df = DataMerger.merge(processed_dfs)
            pipeline_log.append(f"Consolidated total records: {len(self.consolidated_df)}")
            
            # Enable actions
            self.root.after(0, lambda: self.update_ui_post_success(pipeline_log, validation_warnings))
        else:
            pipeline_log.append("\nPipeline failed: No records successfully transformed.")
            self.root.after(0, lambda: self.update_ui_post_failure(pipeline_log))

    def update_ui_post_success(self, log, warnings):
        self.status_label.configure(text="Status: Completed", foreground="#16A34A")
        self.run_btn.configure(state='normal')
        self.export_btn.configure(state='normal')
        self.confluence_btn.configure(state='normal')
        
        self.summary_text.configure(state='normal')
        self.summary_text.delete('1.0', 'end')
        self.summary_text.insert('end', "\n".join(log))
        
        if warnings:
            self.summary_text.insert('end', "\n\n⚠️ VALIDATION WARNINGS:\n")
            self.summary_text.insert('end', "\n".join(warnings))
        self.summary_text.configure(state='disabled')
        messagebox.showinfo("Success", f"Consolidation complete. Consolidated {len(self.consolidated_df)} records.")

    def update_ui_post_failure(self, log):
        self.status_label.configure(text="Status: Failed", foreground="#DC2626")
        self.run_btn.configure(state='normal')
        self.export_btn.configure(state='disabled')
        self.confluence_btn.configure(state='disabled')
        
        self.summary_text.configure(state='normal')
        self.summary_text.delete('1.0', 'end')
        self.summary_text.insert('end', "\n".join(log))
        self.summary_text.configure(state='disabled')
        messagebox.showerror("Error", "Consolidation failed. No regional data could be processed.")

    def action_save_excel(self):
        if self.consolidated_df is None or self.consolidated_df.empty:
            return
            
        save_path = filedialog.asksaveasfilename(
            title="Save Consolidated Excel Workbook",
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile="Final_Report.xlsx"
        )
        if save_path:
            try:
                excel_bytes = DataExporter.export_to_excel(self.consolidated_df)
                with open(save_path, "wb") as f:
                    f.write(excel_bytes)
                logger.info(f"Consolidated Excel saved to: {save_path}")
                messagebox.showinfo("Saved", f"Excel workbook saved successfully:\n{save_path}")
            except Exception as e:
                logger.error(f"Failed to save Excel workbook: {e}")
                messagebox.showerror("Save Error", f"Failed to save Excel workbook: {e}")

    def action_generate_confluence(self):
        if self.consolidated_df is None or self.consolidated_df.empty:
            return
            
        save_dir = filedialog.askdirectory(title="Select Folder to Save Confluence Markup")
        if save_dir:
            try:
                # 1. XML
                xml_markup = ConfluenceGenerator.generate_confluence_xml(self.consolidated_df)
                xml_path = os.path.join(save_dir, "Confluence_Storage_Format.xml")
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(xml_markup)
                    
                # 2. HTML
                html_markup = ConfluenceGenerator.generate_pure_html(self.consolidated_df)
                html_path = os.path.join(save_dir, "Confluence_HTML_Fallback.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_markup)
                    
                logger.info(f"Confluence markups generated in: {save_dir}")
                messagebox.showinfo("Saved", f"Generated Confluence collaboration files in:\n{save_dir}")
            except Exception as e:
                logger.error(f"Failed to generate Confluence markup: {e}")
                messagebox.showerror("Export Error", f"Failed to generate Confluence files: {e}")

    # --- TAB 2: STANDARD MAPPINGS ---
    def build_mappings_tab(self):
        # Left Panel - Column Mappings
        col_frame = ttk.Frame(self.tab_mappings)
        col_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        col_header = ttk.Label(col_frame, text="Active Column Header Mappings", font=('Segoe UI', 11, 'bold'))
        col_header.pack(anchor='w', pady=(0, 5))
        
        col_scroll = ttk.Scrollbar(col_frame)
        col_scroll.pack(side='right', fill='y')
        
        self.col_tree = ttk.Treeview(col_frame, columns=("source", "target"), show='headings', yscrollcommand=col_scroll.set)
        self.col_tree.heading("source", text="Source Header (Raw Excel)")
        self.col_tree.heading("target", text="Standardized Target Header")
        self.col_tree.column("source", width=220)
        self.col_tree.column("target", width=220)
        self.col_tree.pack(fill='both', expand=True)
        col_scroll.config(command=self.col_tree.yview)
        
        # Form to add column mapping
        col_form = ttk.LabelFrame(col_frame, text="Add Column Mapping Rule", padding=10)
        col_form.pack(fill='x', pady=(10, 0))
        
        ttk.Label(col_form, text="Raw Header:").pack(side='left', padx=5)
        self.entry_col_src = ttk.Entry(col_form, width=15)
        self.entry_col_src.pack(side='left', padx=5)
        
        ttk.Label(col_form, text="Target:").pack(side='left', padx=5)
        self.combo_col_tgt = ttk.Combobox(col_form, values=["Testcase ID", "Testcase Status", "Module", "Function", "Tester", "Comment"], width=15)
        self.combo_col_tgt.set("Module")
        self.combo_col_tgt.pack(side='left', padx=5)
        
        add_col_btn = ttk.Button(col_form, text="Add Rule", command=self.action_add_col_mapping)
        add_col_btn.pack(side='left', padx=5)

        # Right Panel - Status Standardizations
        status_frame = ttk.Frame(self.tab_mappings)
        status_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        status_header = ttk.Label(status_frame, text="Active Status Value Mappings", font=('Segoe UI', 11, 'bold'))
        status_header.pack(anchor='w', pady=(0, 5))
        
        status_scroll = ttk.Scrollbar(status_frame)
        status_scroll.pack(side='right', fill='y')
        
        self.status_tree = ttk.Treeview(status_frame, columns=("source", "target"), show='headings', yscrollcommand=status_scroll.set)
        self.status_tree.heading("source", text="Raw Status Value")
        self.status_tree.heading("target", text="Standardized Value (NA/Blocked)")
        self.status_tree.column("source", width=220)
        self.status_tree.column("target", width=220)
        self.status_tree.pack(fill='both', expand=True)
        status_scroll.config(command=self.status_tree.yview)
        
        # Form to add status mapping
        status_form = ttk.LabelFrame(status_frame, text="Add Status Standardization Rule", padding=10)
        status_form.pack(fill='x', pady=(10, 0))
        
        ttk.Label(status_form, text="Raw Status:").pack(side='left', padx=5)
        self.entry_status_src = ttk.Entry(status_form, width=15)
        self.entry_status_src.pack(side='left', padx=5)
        
        ttk.Label(status_form, text="Standard:").pack(side='left', padx=5)
        self.combo_status_tgt = ttk.Combobox(status_form, values=["NA", "Blocked"], width=10)
        self.combo_status_tgt.set("Blocked")
        self.combo_status_tgt.pack(side='left', padx=5)
        
        add_status_btn = ttk.Button(status_form, text="Add Rule", command=self.action_add_status_mapping)
        add_status_btn.pack(side='left', padx=5)
        
        # Populate Mapping Trees
        self.refresh_mappings_trees()

    def refresh_mappings_trees(self):
        # Clear
        self.col_tree.delete(*self.col_tree.get_children())
        self.status_tree.delete(*self.status_tree.get_children())
        
        # Populate Column mapping
        col_rules = self.mappings.get("column_mapping", {})
        for src, tgt in col_rules.items():
            self.col_tree.insert("", "end", values=(src, tgt))
            
        # Populate Status mapping
        status_rules = self.mappings.get("value_mapping", {}).get("Testcase Status", {})
        for src, tgt in status_rules.items():
            self.status_tree.insert("", "end", values=(src, tgt))

    def action_add_col_mapping(self):
        src = self.entry_col_src.get().strip()
        tgt = self.combo_col_tgt.get().strip()
        if not src or not tgt:
            return
            
        self.mappings["column_mapping"][src] = tgt
        self.save_mappings_config()
        self.refresh_mappings_trees()
        self.entry_col_src.delete(0, 'end')
        logger.info(f"Added column mapping: {src} -> {tgt}")

    def action_add_status_mapping(self):
        src = self.entry_status_src.get().strip()
        tgt = self.combo_status_tgt.get().strip()
        if not src or not tgt:
            return
            
        if "value_mapping" not in self.mappings:
            self.mappings["value_mapping"] = {}
        if "Testcase Status" not in self.mappings["value_mapping"]:
            self.mappings["value_mapping"]["Testcase Status"] = {}
            
        self.mappings["value_mapping"]["Testcase Status"][src] = tgt
        self.save_mappings_config()
        self.refresh_mappings_trees()
        self.entry_status_src.delete(0, 'end')
        logger.info(f"Added status mapping: {src} -> {tgt}")


    # --- TAB 3: LOCAL AI ASSISTANT ---
    def build_ai_tab(self):
        # Left Panel - AI Config & Info
        config_frame = ttk.LabelFrame(self.tab_ai, text="Local AI Service Settings", padding=15, width=320)
        config_frame.pack(side='left', fill='both', padx=(0, 15))
        config_frame.pack_propagate(False)
        
        ttk.Label(config_frame, text="Service Host Address:").pack(anchor='w', pady=(0, 2))
        self.entry_ollama_host = ttk.Entry(config_frame)
        self.entry_ollama_host.insert(0, self.ollama_config.get("ollama_host", "http://localhost:11434"))
        self.entry_ollama_host.pack(fill='x', pady=(0, 12))
        
        self.check_connection_btn = ttk.Button(config_frame, text="🔗 Connect Local Engine", command=self.action_connect_ollama)
        self.check_connection_btn.pack(fill='x', pady=(0, 15))
        
        self.ai_status_label = ttk.Label(config_frame, text="Status: Checking...", font=('Segoe UI', 10, 'bold'), foreground='#475569')
        self.ai_status_label.pack(anchor='w', pady=(0, 15))
        
        ttk.Label(config_frame, text="Active Model:").pack(anchor='w', pady=(0, 2))
        self.combo_ollama_model = ttk.Combobox(config_frame, state='disabled')
        self.combo_ollama_model.pack(fill='x', pady=(0, 20))
        
        # Info note
        info_note = tk.Message(
            config_frame,
            text="💡 The local AI Assistant queries your Ollama models locally on your host CPU/GPU.\n\nAll spreadsheet analysis remains 100% offline, keeping sensitive data safe from external server uploads.",
            font=('Segoe UI', 9),
            foreground='#64748B',
            width=280
        )
        info_note.pack(fill='x', side='bottom')

        # Right Panel - Conversational Chat Box
        chat_frame = ttk.LabelFrame(self.tab_ai, text="Conversational Report Query Assistant", padding=15)
        chat_frame.pack(side='right', fill='both', expand=True)
        
        # Chat History
        history_scroll = ttk.Scrollbar(chat_frame)
        history_scroll.pack(side='right', fill='y')
        
        self.chat_history = tk.Text(chat_frame, wrap='word', state='disabled', font=('Segoe UI', 10), yscrollcommand=history_scroll.set, relief='solid', borderwidth=1)
        self.chat_history.pack(fill='both', expand=True, pady=(0, 10))
        history_scroll.config(command=self.chat_history.yview)
        
        # Chat Input Frame
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill='x')
        
        self.chat_entry = ttk.Entry(input_frame)
        self.chat_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", lambda e: self.action_send_query())
        
        self.send_btn = ttk.Button(input_frame, text="💬 Ask AI", style="Primary.TButton", command=self.action_send_query, state='disabled')
        self.send_btn.pack(side='right', ipady=4)

    def init_ollama_engine(self):
        host = self.ollama_config.get("ollama_host", "http://localhost:11434")
        self.ollama_mapper = OllamaMapper(host=host)
        is_connected, models = self.ollama_mapper.check_connection()
        models = list(dict.fromkeys(models))
        
        if is_connected:
            self.root.after(0, lambda: self.update_ollama_ui_success(models))
        else:
            self.root.after(0, self.update_ollama_ui_failure)

    def action_connect_ollama(self):
        host = self.entry_ollama_host.get().strip()
        if not host:
            return
            
        self.ai_status_label.configure(text="Connecting...", foreground="#D97706")
        self.check_connection_btn.configure(state='disabled')
        
        # Check connection in background thread
        def check():
            mapper = OllamaMapper(host=host)
            is_connected, models = mapper.check_connection()
            models = list(dict.fromkeys(models))
            
            # Save parameters if successful
            if is_connected:
                self.ollama_mapper = mapper
                self.ollama_config["ollama_host"] = host
                self.save_ollama_config()
                self.root.after(0, lambda: self.update_ollama_ui_success(models))
            else:
                self.root.after(0, self.update_ollama_ui_failure)
                
        threading.Thread(target=check, daemon=True).start()

    def update_ollama_ui_success(self, models):
        self.ai_status_label.configure(text="🟢 Engine Connected", foreground="#16A34A")
        self.check_connection_btn.configure(state='normal')
        
        if models:
            self.combo_ollama_model.configure(state='readonly', values=models)
            saved_model = self.ollama_config.get("selected_model")
            if saved_model and saved_model in models:
                self.combo_ollama_model.set(saved_model)
            else:
                self.combo_ollama_model.set(models[0])
            self.send_btn.configure(state='normal')
        else:
            self.combo_ollama_model.configure(state='disabled')
            self.combo_ollama_model.set("No models installed")
            self.send_btn.configure(state='disabled')
            logger.warning("Ollama connection succeeded but found no installed models. Run 'ollama pull llama3' locally.")

    def update_ollama_ui_failure(self):
        self.ai_status_label.configure(text="🔴 Engine Offline", foreground="#DC2626")
        self.check_connection_btn.configure(state='normal')
        self.combo_ollama_model.configure(state='disabled')
        self.combo_ollama_model.set("Service offline")
        self.send_btn.configure(state='disabled')

    def action_send_query(self):
        question = self.chat_entry.get().strip()
        if not question or self.ollama_mapper is None:
            return
            
        if self.consolidated_df is None or self.consolidated_df.empty:
            messagebox.showwarning("No Data", "Please load and consolidate your files first to enable querying.")
            return
            
        model = self.combo_ollama_model.get()
        if not model:
            return
            
        # Clear entry and save model preference
        self.chat_entry.delete(0, 'end')
        self.ollama_config["selected_model"] = model
        self.save_ollama_config()
        
        # Append question to chat area
        self.append_to_chat(f"👤 Question:\n{question}\n")
        self.append_to_chat("🤖 Assistant:\nThinking...\n")
        
        self.send_btn.configure(state='disabled')
        self.chat_entry.configure(state='disabled')
        
        # Run AI mapping/querying on background thread
        def ask():
            try:
                answer = self.ollama_mapper.query_report(
                    df=self.consolidated_df,
                    question=question,
                    model=model
                )
                self.root.after(0, lambda: self.update_chat_with_answer(answer))
            except Exception as e:
                self.root.after(0, lambda: self.update_chat_with_error(str(e)))
                
        threading.Thread(target=ask, daemon=True).start()

    def update_chat_with_answer(self, answer):
        # Remove the 'Thinking...' placeholder (last line/characters)
        self.chat_history.configure(state='normal')
        
        # Simple backspace delete of "Thinking...\n"
        self.chat_history.delete("end - 2 lines linestart", "end - 1 chars")
        self.chat_history.insert('end', f"{answer}\n")
        self.chat_history.insert('end', "━" * 55 + "\n")
        self.chat_history.configure(state='disabled')
        self.chat_history.see('end')
        
        self.send_btn.configure(state='normal')
        self.chat_entry.configure(state='normal')
        self.chat_entry.focus()

    def update_chat_with_error(self, err_msg):
        self.chat_history.configure(state='normal')
        self.chat_history.delete("end - 2 lines linestart", "end - 1 chars")
        self.chat_history.insert('end', f"Error querying local AI service: {err_msg}\n")
        self.chat_history.insert('end', "━" * 55 + "\n")
        self.chat_history.configure(state='disabled')
        self.chat_history.see('end')
        
        self.send_btn.configure(state='normal')
        self.chat_entry.configure(state='normal')
        self.chat_entry.focus()

    def append_to_chat(self, msg):
        self.chat_history.configure(state='normal')
        self.chat_history.insert('end', msg)
        self.chat_history.configure(state='disabled')
        self.chat_history.see('end')


    # --- TAB 4: SYSTEM LOGS ---
    def build_logs_tab(self):
        log_scroll = ttk.Scrollbar(self.tab_logs)
        log_scroll.pack(side='right', fill='y')
        
        self.log_text = tk.Text(self.tab_logs, wrap='none', font=('Consolas', 10), state='disabled', background='#1E293B', foreground='#E2E8F0', yscrollcommand=log_scroll.set)
        self.log_text.pack(fill='both', expand=True)
        log_scroll.config(command=self.log_text.yview)

    def connect_log_handler(self):
        # Bind the logging stream directly to the text frame log console
        root_logger = logging.getLogger("test_report")
        self.text_handler = TextHandler(self.log_text)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.text_handler.setFormatter(formatter)
        root_logger.addHandler(self.text_handler)

def main():
    root = tk.Tk()
    app = DesktopApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
