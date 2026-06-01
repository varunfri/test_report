import pandas as pd
import os

def populate_unfiltered_reports():
    unfiltered_dir = "report/un_filtered_report"
    
    # Check if directory exists
    if not os.path.exists(unfiltered_dir):
        print(f"Error: {unfiltered_dir} does not exist.")
        return

    # List of files to populate with duplicates
    files = {
        "us_report.xlsx": [
            {
                "No": 1, "Module": "Module_F", "Function": "Billing", "Testcase ID": "US_TC_001", 
                "Testcase Status": "Blocked", "Tester": "Dave", "Comment": "Server offline", "seq": 1
            },
            {
                "No": 2, "Module": "Module_F", "Function": "Billing", "Testcase ID": "US_TC_001", 
                "Testcase Status": "Blocked", "Tester": "Dave", "Comment": "US Duplicate sequence 2", "seq": 2
            },
            {
                "No": 3, "Module": "Module_F", "Function": "Auth", "Testcase ID": "US_TC_002", 
                "Testcase Status": "Fail", "Tester": "Dave", "Comment": "Fail", "seq": 1
            },
            {
                "No": 4, "Module": "Module_G", "Function": "Database", "Testcase ID": "US_TC_003", 
                "Testcase Status": "NA", "Tester": "Dave", "Comment": "Not needed", "seq": 1
            }
        ],
        "cn_report.xlsx": [
            {
                "No": 1, "Module": "Module_A", "Function": "Network", "Testcase ID": "CN_TC_001", 
                "Testcase Status": "NA", "Tester": "Alice", "Comment": "No CN scope", "seq": 1
            },
            {
                "No": 2, "Module": "Module_B", "Function": "UI Layout", "Testcase ID": "CN_TC_002", 
                "Testcase Status": "Blocked", "Tester": "Alice", "Comment": "Hardware blocked", "seq": 1
            },
            {
                "No": 3, "Module": "Module_B", "Function": "UI Layout", "Testcase ID": "CN_TC_002", 
                "Testcase Status": "Blocked", "Tester": "Alice", "Comment": "CN Duplicate sequence 2", "seq": 2
            }
        ],
        "eu_report.xlsx": [
            {
                "No": 1, "Module": "Module_C", "Function": "Storage", "Testcase ID": "EU_TC_001", 
                "Testcase Status": "Not Applicable", "Tester": "Bob", "Comment": "Out of scope", "seq": 1
            },
            {
                "No": 2, "Module": "Module_C", "Function": "Bluetooth", "Testcase ID": "EU_TC_002", 
                "Testcase Status": "BLOCK", "Tester": "Bob", "Comment": "API blocked", "seq": 1
            },
            {
                "No": 3, "Module": "Module_C", "Function": "Bluetooth", "Testcase ID": "EU_TC_002", 
                "Testcase Status": "BLOCK", "Tester": "Bob", "Comment": "EU Duplicate sequence 2", "seq": 2
            }
        ],
        "jp_report.xlsx": [
            {
                "No": 1, "Module": "Module_D", "Function": "Audio", "Testcase ID": "JP_TC_001", 
                "Testcase Status": "Pass", "Tester": "Charlie", "Comment": "Success", "seq": 1
            },
            {
                "No": 2, "Module": "Module_E", "Function": "Sensors", "Testcase ID": "JP_TC_002", 
                "Testcase Status": "Dependency", "Tester": "Charlie", "Comment": "Awaiting hardware", "seq": 1
            },
            {
                "No": 3, "Module": "Module_E", "Function": "Sensors", "Testcase ID": "JP_TC_002", 
                "Testcase Status": "Dependency", "Tester": "Charlie", "Comment": "JP Duplicate sequence 3", "seq": 3
            }
        ]
    }

    # Scan report/un_filtered_report and map files to region dynamically
    for f in sorted(os.listdir(unfiltered_dir)):
        if f.endswith(".xlsx") and not f.startswith("~$"):
            file_path = os.path.join(unfiltered_dir, f)
            
            # Map region based on filename codes
            region_key = None
            if ".AUS" in f or "us_" in f.lower():
                region_key = "us_report.xlsx"
            elif ".AWZ" in f or "cn_" in f.lower():
                region_key = "cn_report.xlsx"
            elif ".AEU" in f or "eu_" in f.lower():
                region_key = "eu_report.xlsx"
            elif ".AJL" in f or "jp_" in f.lower():
                region_key = "jp_report.xlsx"
                
            if not region_key or region_key not in files:
                print(f"Skipping {f} because it could not be mapped to a known regional template.")
                continue
                
            rows = files[region_key]
            
            # Load the empty sheet's columns
            df_empty = pd.read_excel(file_path)
            cols = list(df_empty.columns)
            
            # Build new DataFrame with the same columns
            data = {col: [] for col in cols}
            
            for row in rows:
                for col in cols:
                    # Find matching dictionary key case-insensitively
                    matched_key = next((k for k in row.keys() if k.lower() == col.lower()), None)
                    val = row[matched_key] if matched_key is not None else ""
                    data[col].append(val)
                    
            df_new = pd.DataFrame(data)
            df_new.to_excel(file_path, index=False)
            print(f"Populated {f} (mapped from {region_key}) with {len(rows)} test rows.")

if __name__ == "__main__":
    populate_unfiltered_reports()
