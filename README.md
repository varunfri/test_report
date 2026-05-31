# NA, Blocked Consolidation & Confluence Collaboration Tool

A modular, configuration-driven Python application with a Streamlit user interface and local Ollama AI assistant. It standardizes, validates, and merges regional Excel test reports, splitting output records into dedicated worksheets per region with dynamic status cell coloring, and generating copyable Confluence Deck/Card/Expand macro collaboration layouts.

---

## Workspace Structure

```text
test_report/
├── app.py                     # Primary Streamlit Dashboard
├── requirements.txt           # Python dependencies list
├── run.command                # Double-clickable macOS launcher script
├── run.bat                    # Double-clickable Windows batch launcher
├── run.sh                     # Generic Linux shell launcher script
├── .gitignore                 # Excluded directories and metadata

│
├── config/                    # Processing Configurations
│   ├── mappings.yaml          # Column maps and status translations
│   └── filters.yaml           # Target allowed status filters
│
├── services/                  # Core Processing Pipeline
│   ├── loader.py              # Safe Excel loader (keeps NA strings)
│   ├── validator.py           # Schema and value validation
│   ├── transformer.py         # Mappings, status filters, and metadata injection
│   ├── merger.py              # DataFrame concatenation
│   ├── exporter.py            # Styled Excel generator (regional tabs, custom colors)
│   ├── confluence.py          # Confluence Storage Format XHTML and HTML generator
│   └── logger.py              # Centralized logging service (writes to console and output/app.log)
│
├── llm/                       # Local AI integration
│   └── column_mapper.py       # Local Ollama REST API interface
│
├── scripts/                   # Relocated Developer Utilities
│   ├── generate_samples.py    # Generates regional empty templates
│   ├── populate_reports.py    # Populates templates with mock test data
│   ├── verify_pipeline.py     # Command-line integration test harness
│   └── generate_confluence_markup.py # Generates XML/HTML markup files from output
│
├── report/                    # Source spreadsheets
│   ├── un_filtered_report/    # Uploadable regional reports
│   └── filtered_report/       # Expected format structure reference
│
├── uploads/                   # Persistent workspace folder for uploaded files
└── output/                    # Folder containing generated outputs
```

---

## Getting Started

### Simple Launcher (Recommended for Non-Technical Users)

To run the application and set up the environment automatically, execute the appropriate file for your platform:

- **macOS**: Double-click `run.command` in Finder.
- **Windows**: Double-click `run.bat` in File Explorer.
- **Linux**: Execute `./run.sh` in the terminal.

These scripts automatically verify if Python is installed, configure a private virtual environment (`.venv`), install the necessary libraries from `requirements.txt`, and start the Streamlit web dashboard. Once started, open **`http://localhost:8501`** in your browser to interact with the interface.

### Manual Terminal Method (For Developers)

If you prefer to configure and run the application manually:

1. Initialize and activate the virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the Streamlit server from the workspace root:
   ```bash
   streamlit run app.py
   ```
3. Open **`http://localhost:8501`** in your browser to interact with the dashboard.

---

## Developer Utility Commands

To quickly test the application locally with mock data:

1. **Populate templates with mock test cases**:
   ```bash
   python3 scripts/populate_reports.py
   ```
2. **Execute the programmatic verification pipeline**:
   ```bash
   python3 scripts/verify_pipeline.py
   ```
3. **Generate Confluence collaboration markup files**:
   ```bash
   python3 scripts/generate_confluence_markup.py
   ```

Outputs are generated inside the `output/` directory as `Final_Report.xlsx`, `Confluence_Storage_Format.xml`, and `Confluence_HTML_Fallback.html`.

---

## Detailed Specifications

### 1. Excel Exporter Features (`services/exporter.py`)

- **Regional Worksheets**: The exporter splits consolidated data into separate tabs based on region (`US`, `CN`, `EU`, `JP`) alongside a primary `Statistics` pivot summary worksheet.
- **Dynamic Cell Styling**: Cells in the `Testcase Status` column are dynamically highlighted based on status:
  - **`Blocked`**: Soft red fill (`#FEE2E2`) and dark red bold font (`#991B1B`).
  - **`NA`**: Soft blue fill (`#DBEAFE`) and dark blue bold font (`#1E40AF`).
- **Autofit and Gridlines**: Auto-adjusts column widths to padding + 4, with visible gridlines.

### 2. Confluence Exporter Features (`services/confluence.py`)

Generates structured XHTML layout to paste directly into the Confluence page editor:

- **Deck & Card Macros**: Outer-level grouping with cards labeled **`NA`** and **`Blocked`**.
- **Native Expand Macros**: Nested region-level tabs (e.g. `Expand (US Region)`) containing formatted HTML data tables listing testcase IDs, models, functions, testers, and comments.

### 3. Local Ollama AI Assistant (`llm/column_mapper.py`)

- Connects to the local Ollama instance (default: `http://localhost:11434`).
- Uses JSON-mode API requests to let a local model (like `llama3`) dynamically map non-standard spreadsheet column headers and translate unknown status cell strings, with built-in rule-based fallbacks.
- Keeps sensitive company spreadsheet data offline and private.
