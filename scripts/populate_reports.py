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
                "No": 1, "Models": "Model_F", "Function": "Billing", "Testcase ID": "US_TC_001", 
                "Testcase Status": "Blocked", "Tester": "Dave", "Comment": "Server offline", "seq": 1
            },
            {
                "No": 2, "Models": "Model_F", "Function": "Billing", "Testcase ID": "US_TC_001", 
                "Testcase Status": "Blocked", "Tester": "Dave", "Comment": "US Duplicate sequence 2", "seq": 2
            },
            {
                "No": 3, "Models": "Model_F", "Function": "Auth", "Testcase ID": "US_TC_002", 
                "Testcase Status": "Fail", "Tester": "Dave", "Comment": "Fail", "seq": 1
            },
            {
                "No": 4, "Models": "Model_G", "Function": "Database", "Testcase ID": "US_TC_003", 
                "Testcase Status": "NA", "Tester": "Dave", "Comment": "Not needed", "seq": 1
            }
        ],
        "cn_report.xlsx": [
            {
                "No": 1, "Models": "Model_A", "Function": "Network", "Testcase ID": "CN_TC_001", 
                "Testcase Status": "NA", "Tester": "Alice", "Comment": "No CN scope", "seq": 1
            },
            {
                "No": 2, "Models": "Model_B", "Function": "UI Layout", "Testcase ID": "CN_TC_002", 
                "Testcase Status": "Blocked", "Tester": "Alice", "Comment": "Hardware blocked", "seq": 1
            },
            {
                "No": 3, "Models": "Model_B", "Function": "UI Layout", "Testcase ID": "CN_TC_002", 
                "Testcase Status": "Blocked", "Tester": "Alice", "Comment": "CN Duplicate sequence 2", "seq": 2
            }
        ],
        "eu_report.xlsx": [
            {
                "No": 1, "Models": "Model_C", "Function": "Storage", "Testcase ID": "EU_TC_001", 
                "Testcase Status": "Not Applicable", "Tester": "Bob", "Comment": "Out of scope", "seq": 1
            },
            {
                "No": 2, "Models": "Model_C", "Function": "Bluetooth", "Testcase ID": "EU_TC_002", 
                "Testcase Status": "BLOCK", "Tester": "Bob", "Comment": "API blocked", "seq": 1
            },
            {
                "No": 3, "Models": "Model_C", "Function": "Bluetooth", "Testcase ID": "EU_TC_002", 
                "Testcase Status": "BLOCK", "Tester": "Bob", "Comment": "EU Duplicate sequence 2", "seq": 2
            }
        ],
        "jp_report.xlsx": [
            {
                "No": 1, "Models": "Model_D", "Function": "Audio", "Testcase ID": "JP_TC_001", 
                "Testcase Status": "Pass", "Tester": "Charlie", "Comment": "Success", "seq": 1
            },
            {
                "No": 2, "Models": "Model_E", "Function": "Sensors", "Testcase ID": "JP_TC_002", 
                "Testcase Status": "Dependency", "Tester": "Charlie", "Comment": "Awaiting hardware", "seq": 1
            },
            {
                "No": 3, "Models": "Model_E", "Function": "Sensors", "Testcase ID": "JP_TC_002", 
                "Testcase Status": "Dependency", "Tester": "Charlie", "Comment": "JP Duplicate sequence 3", "seq": 3
            }
        ]
    }

    for filename, rows in files.items():
        file_path = os.path.join(unfiltered_dir, filename)
        if not os.path.exists(file_path):
            print(f"Skipping {filename} because it does not exist.")
            continue
            
        # Load the empty sheet's columns
        df_empty = pd.read_excel(file_path)
        cols = list(df_empty.columns)
        
        # Build new DataFrame with the same columns
        data = {col: [] for col in cols}
        
        for row in rows:
            for col in cols:
                # Insert row value if defined, otherwise empty string
                data[col].append(row.get(col, ""))
                
        df_new = pd.DataFrame(data)
        df_new.to_excel(file_path, index=False)
        print(f"Populated {file_path} with {len(rows)} test rows (with sequence duplicates).")

if __name__ == "__main__":
    populate_unfiltered_reports()
