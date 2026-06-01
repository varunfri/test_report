import pandas as pd
import os
import sys
import yaml

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.confluence import ConfluenceGenerator

def main():
    print("=== Generating Confluence Collaboration Markup ===")
    
    # 1. Load consolidated data
    consolidated_file = "output/Final_Report.xlsx"
    
    if not os.path.exists(consolidated_file):
        print(f"Warning: {consolidated_file} not found. Running verify_pipeline.py first to build it...")
        # Try importing verify_pipeline
        try:
            import verify_pipeline
            verify_pipeline.run_verification()
        except Exception as e:
            print(f"Failed to generate pipeline report: {str(e)}")
            return
            
    # Load all worksheets (except Statistics) and concatenate them
    xls = pd.ExcelFile(consolidated_file)
    dfs = []
    for sheet in xls.sheet_names:
        if sheet != "Statistics":
            dfs.append(pd.read_excel(xls, sheet_name=sheet, keep_default_na=False))
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=["Region", "Module", "Function", "Testcase ID", "Tester", "Testcase Status", "Comment"])
    print(f"Loaded {len(df)} consolidated records from regional worksheets.")

    # 2. Generate XML Storage Format (Deck/Card/Expand)
    xml_markup = ConfluenceGenerator.generate_confluence_xml(df)
    xml_path = "output/Confluence_Storage_Format.xml"
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_markup)
    print(f"Created: {xml_path}")

    # 3. Generate HTML Fallback (details/summary tabs)
    html_markup = ConfluenceGenerator.generate_pure_html(df)
    html_path = "output/Confluence_HTML_Fallback.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_markup)
    print(f"Created: {html_path}")

    print("\nSample Confluence XML Output preview (First 20 lines):")
    print("\n".join(xml_markup.splitlines()[:25]))
    print("...")
    print("\n=== Confluence Collaboration Markup generated successfully ===")

if __name__ == "__main__":
    main()
