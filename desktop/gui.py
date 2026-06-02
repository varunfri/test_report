import sys
import os
import shutil
import logging
import json
import yaml
from datetime import datetime
import webview
import pandas as pd

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

# Custom Logging Handler to write Python events in real-time to the JS webview
class WebviewLogHandler(logging.Handler):
    def __init__(self, window):
        super().__init__()
        self.window = window
        
    def emit(self, record):
        msg = self.format(record)
        # Escape characters for safe evaluation inside JavaScript string literal
        safe_msg = msg.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '')
        try:
            self.window.evaluate_js(f"appendLog('{safe_msg}')")
        except Exception:
            pass

class WebviewApi:
    def __init__(self):
        self.window = None
        self.selected_files = []
        self.consolidated_df = None
        self.ollama_mapper = None
        
        # Configure Persistent paths
        if getattr(sys, 'frozen', False):
            exec_path = sys.executable
            # If macOS app bundle, go up 3 levels to exit ReportConsolidationTool.app/Contents/MacOS/ReportConsolidationTool
            if sys.platform == 'darwin' and '.app/Contents/MacOS/' in exec_path:
                exec_dir = os.path.abspath(os.path.join(os.path.dirname(exec_path), "..", "..", ".."))
            else:
                exec_dir = os.path.dirname(exec_path)
            self.config_dir = os.path.join(exec_dir, "config")
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Copy default files from _MEIPASS if they do not exist
            default_config_src = os.path.join(sys._MEIPASS, "config")
            for filename in ["mappings.yaml", "filters.yaml", "ollama_config.json"]:
                src_file = os.path.join(default_config_src, filename)
                dest_file = os.path.join(self.config_dir, filename)
                if not os.path.exists(dest_file) and os.path.exists(src_file):
                    try:
                        shutil.copy2(src_file, dest_file)
                    except Exception as e:
                        print(f"Error copying config {filename}: {e}")
        else:
            self.config_dir = os.path.join(root_path, "config")
            
        self.mappings_path = os.path.join(self.config_dir, "mappings.yaml")
        self.filters_path = os.path.join(self.config_dir, "filters.yaml")
        self.ollama_config_path = os.path.join(self.config_dir, "ollama_config.json")
        
        self.load_configurations()

    def load_configurations(self):
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

        # Mappings Load
        if os.path.exists(self.mappings_path):
            try:
                with open(self.mappings_path, "r") as f:
                    self.mappings = yaml.safe_load(f) or self.default_mappings
            except Exception:
                self.mappings = self.default_mappings
        else:
            self.mappings = self.default_mappings

        # Filters Load
        if os.path.exists(self.filters_path):
            try:
                with open(self.filters_path, "r") as f:
                    self.filters = yaml.safe_load(f) or self.default_filters
            except Exception:
                self.filters = self.default_filters
        else:
            self.filters = self.default_filters

        # Ollama config Load
        if os.path.exists(self.ollama_config_path):
            try:
                with open(self.ollama_config_path, "r") as f:
                    self.ollama_config = json.load(f) or self.default_ollama
            except Exception:
                self.ollama_config = self.default_ollama
        else:
            self.ollama_config = self.default_ollama

    def get_configurations(self):
        result = {
            "column_mapping": self.mappings.get("column_mapping", {}),
            "value_mapping": self.mappings.get("value_mapping", {}),
            "allowed_statuses": self.filters.get("allowed_statuses", [])
        }
        return result

    def save_mappings(self, new_mappings):
        self.mappings["column_mapping"] = new_mappings.get("column_mapping", {})
        self.mappings["value_mapping"] = new_mappings.get("value_mapping", {})
        try:
            with open(self.mappings_path, "w") as f:
                yaml.safe_dump(self.mappings, f, default_flow_style=False)
            logger.info("Saved column and status mappings configuration successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to save mappings configuration: {e}")
            return False

    def check_ollama_engine(self, host):
        self.ollama_mapper = OllamaMapper(host=host)
        is_connected, models = self.ollama_mapper.check_connection()
        models = list(dict.fromkeys(models))
        selected_model = self.ollama_config.get("selected_model")
        return {
            "connected": is_connected,
            "models": models,
            "selected_model": selected_model if selected_model in models else (models[0] if models else None)
        }

    def update_ollama_host(self, host):
        self.ollama_config["ollama_host"] = host
        try:
            with open(self.ollama_config_path, "w") as f:
                json.dump(self.ollama_config, f, indent=2)
            logger.info(f"Ollama server address updated to: {host}")
            return True
        except Exception as e:
            logger.error(f"Failed to update Ollama settings: {e}")
            return False

    def browse_excel_files(self):
        if not self.window:
            return []
        file_types = ('Excel Files (*.xlsx)', '*.xlsx')
        paths = self.window.create_file_dialog(
            webview.OPEN_DIALOG, 
            allow_multiple=True, 
            file_types=(file_types,)
        )
        return list(paths) if paths else []

    def run_consolidation(self, file_paths, release, date):
        self.selected_files = file_paths
        
        col_mapping = self.mappings.get("column_mapping", {})
        value_mapping = self.mappings.get("value_mapping", {})
        allowed_statuses = set(self.filters.get("allowed_statuses", ["NA", "Blocked"]))
        
        processed_dfs = []
        validation_warnings = []
        
        for path in self.selected_files:
            filename = os.path.basename(path)
            logger.info(f"Processing sheet: {filename}")
            
            try:
                df = FileLoader.load_sheet(path)
                logger.info(f"  - Loaded {len(df)} rows.")
            except Exception as e:
                logger.error(f"Error loading file {filename}: {e}")
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
                
            # Validate
            validator = DataValidator(target_columns=["Testcase ID", "Testcase Status"])
            report = validator.validate(df, col_mapping, allowed_statuses)
            
            if report["warnings"]:
                for warn in report["warnings"]:
                    validation_warnings.append(f"[{filename}] {warn}")
            
            if not report["is_valid"]:
                logger.warning(f"Validation failure in {filename}. Skipping. Missing: {report['missing_expected_columns']}")
                continue
                
            # Transform
            try:
                df_trans = DataTransformer.transform(
                    df=df,
                    col_mapping=col_mapping,
                    value_mapping=value_mapping,
                    allowed_statuses=allowed_statuses,
                    region=region,
                    execution_date=date,
                    release=release,
                    keep_all_columns=False
                )
                processed_dfs.append(df_trans)
                logger.info(f"  - Successfully transformed {len(df_trans)} valid rows.")
            except Exception as e:
                logger.error(f"Error transforming {filename}: {e}")

        if processed_dfs:
            self.consolidated_df = DataMerger.merge(processed_dfs)
            logger.info(f"Merged successfully. Consolidated total: {len(self.consolidated_df)} records.")
            
            # Count metrics
            total_rows = len(self.consolidated_df)
            total_na = len(self.consolidated_df[self.consolidated_df["Testcase Status"] == "NA"])
            total_blocked = len(self.consolidated_df[self.consolidated_df["Testcase Status"] == "Blocked"])
            
            return {
                "success": True,
                "metrics": {
                    "total_rows": total_rows,
                    "total_na": total_na,
                    "total_blocked": total_blocked
                },
                "warnings": validation_warnings,
                "error": None
            }
        else:
            return {
                "success": False,
                "metrics": {
                    "total_rows": 0,
                    "total_na": 0,
                    "total_blocked": 0
                },
                "warnings": [],
                "error": "No files were successfully processed. Please verify your standard column mappings and files."
            }

    def save_consolidated_excel(self):
        if self.consolidated_df is None or self.consolidated_df.empty or not self.window:
            return None
            
        file_types = ('Excel Files (*.xlsx)', '*.xlsx')
        save_path = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory='',
            save_filename='Final_Report.xlsx',
            file_types=(file_types,)
        )
        if save_path:
            try:
                excel_bytes = DataExporter.export_to_excel(self.consolidated_df)
                with open(save_path, "wb") as f:
                    f.write(excel_bytes)
                logger.info(f"Consolidated workbook saved to: {save_path}")
                return save_path
            except Exception as e:
                logger.error(f"Failed to save Excel file: {e}")
        return None

    def save_confluence_markup(self):
        if self.consolidated_df is None or self.consolidated_df.empty or not self.window:
            return None
            
        save_dir = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if save_dir:
            try:
                # Storage format
                xml_markup = ConfluenceGenerator.generate_confluence_xml(self.consolidated_df)
                xml_path = os.path.join(save_dir, "Confluence_Storage_Format.xml")
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(xml_markup)
                    
                # HTML fallback
                html_markup = ConfluenceGenerator.generate_pure_html(self.consolidated_df)
                html_path = os.path.join(save_dir, "Confluence_HTML_Fallback.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_markup)
                    
                logger.info(f"Confluence integration files written inside: {save_dir}")
                return save_dir
            except Exception as e:
                logger.error(f"Failed to export Confluence markups: {e}")
        return None

    def query_assistant(self, question, model):
        if self.consolidated_df is None or self.consolidated_df.empty:
            return "Please consolidate reports first before querying the AI."
            
        self.ollama_config["selected_model"] = model
        try:
            with open(self.ollama_config_path, "w") as f:
                json.dump(self.ollama_config, f, indent=2)
        except Exception:
            pass
            
        if not self.ollama_mapper:
            host = self.ollama_config.get("ollama_host", "http://localhost:11434")
            self.ollama_mapper = OllamaMapper(host=host)
            
        try:
            answer = self.ollama_mapper.query_report(
                df=self.consolidated_df,
                question=question,
                model=model
            )
            return answer
        except Exception as e:
            logger.error(f"Error querying AI model: {e}")
            return f"Error querying local AI service: {e}"

def main():
    api = WebviewApi()
    
    # Resolve the UI file path (dev vs frozen)
    if getattr(sys, 'frozen', False):
        ui_path = os.path.join(sys._MEIPASS, "ui", "index.html")
    else:
        ui_path = os.path.join(base_path, "ui", "index.html")
        
    window = webview.create_window(
        title="NA, Blocked Report Generator - Standalone App",
        url=ui_path,
        js_api=api,
        width=1280,
        height=850,
        resizable=True
    )
    api.window = window
    
    # Connect system log handler to webview console
    root_logger = logging.getLogger("test_report")
    log_handler = WebviewLogHandler(window)
    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    log_handler.setFormatter(log_formatter)
    root_logger.addHandler(log_handler)
    
    # Start webview app loop
    webview.start()

if __name__ == "__main__":
    main()
