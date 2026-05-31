import pandas as pd
import yaml
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.loader import FileLoader
from services.validator import DataValidator
from services.transformer import DataTransformer
from services.merger import DataMerger
from services.exporter import DataExporter

def run_verification():
    print("=== Starting Core Pipeline Verification with Real Report Formats ===")
    
    # 1. Load Configurations
    with open("config/mappings.yaml", "r") as f:
        mappings = yaml.safe_load(f)
    with open("config/filters.yaml", "r") as f:
        filters = yaml.safe_load(f)
        
    col_mapping = mappings["column_mapping"]
    value_mapping = mappings["value_mapping"]
    allowed_statuses = set(filters["allowed_statuses"])
    
    print(f"Loaded {len(col_mapping)} column mapping rules.")
    print(f"Allowed target statuses: {allowed_statuses}")

    # 2. Regional Files metadata
    files_meta = [
        {"path": "report/un_filtered_report/us_report.xlsx", "region": "US"},
        {"path": "report/un_filtered_report/cn_report.xlsx", "region": "CN"},
        {"path": "report/un_filtered_report/eu_report.xlsx", "region": "EU"},
        {"path": "report/un_filtered_report/jp_report.xlsx", "region": "JP"}
    ]
    
    processed_dfs = []
    
    # 3. Process each file
    for item in files_meta:
        path = item["path"]
        region = item["region"]
        
        if not os.path.exists(path):
            print(f"Error: file not found {path}")
            continue
            
        print(f"\nProcessing {path} (Region: {region})...")
        
        # Load
        df = FileLoader.load_sheet(path)
        print(f"  Loaded {len(df)} rows. Columns: {list(df.columns)[:5]} ... (total {len(df.columns)} columns)")
        
        # Validate
        validator = DataValidator(target_columns=["Testcase ID", "Testcase Status"])
        report = validator.validate(df, col_mapping, allowed_statuses)
        
        print(f"  Validation - Valid: {report['is_valid']}")
        print(f"  Validation - Errors: {report['errors']}")
        print(f"  Validation - Warnings: {report['warnings']}")
        
        if not report["is_valid"]:
            print(f"  Skipping {region} due to validation errors.")
            continue
            
        # Transform
        df_trans = DataTransformer.transform(
            df=df,
            col_mapping=col_mapping,
            value_mapping=value_mapping,
            allowed_statuses=allowed_statuses,
            region=region,
            execution_date="2026-05-31",
            release="v1.0",
            keep_all_columns=False
        )
        print(f"  Transformed to {len(df_trans)} rows.")
        processed_dfs.append(df_trans)

    # 4. Merge
    print("\nMerging all transformed reports...")
    consolidated_df = DataMerger.merge(processed_dfs)
    print(f"Consolidated total records: {len(consolidated_df)}")
    print(consolidated_df)

    # 5. Export
    os.makedirs("output", exist_ok=True)
    excel_bytes = DataExporter.export_to_excel(consolidated_df)
    
    output_path = "output/Final_Report.xlsx"
    with open(output_path, "wb") as f:
        f.write(excel_bytes)
    print(f"\nExported beautifully styled final workbook to: {output_path}")
    print("=== Core Pipeline Verification Completed successfully ===")

if __name__ == "__main__":
    run_verification()
