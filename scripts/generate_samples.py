import pandas as pd
import os

def create_sample_files():
    # Make sure output directories exist
    os.makedirs("sample_data", exist_ok=True)
    
    # 1. US Report
    us_data = {
        "Test_ID": ["TC001", "TC002", "TC003", "TC004", "TC005"],
        "Status": ["NA", "Blocked", "Pass", "Fail", "Blocked"],
        "Comment": ["No US scope", "Dependency on billing API", "Verified", "Button alignment issue", "Data sync lag"]
    }
    pd.DataFrame(us_data).to_excel("sample_data/US.xlsx", index=False)
    print("Created sample_data/US.xlsx")

    # 2. EU Report (using TC_ID and Blocked/Not Applicable variations)
    eu_data = {
        "TC_ID": ["TC101", "TC102", "TC103", "TC104"],
        "Status": ["Not Applicable", "BLOCK", "Pass", "Dependency"],
        "Details": ["No EU scope", "Blocked by environment configuration", "Verified", "Blocked by network settings"]
    }
    pd.DataFrame(eu_data).to_excel("sample_data/EU.xlsx", index=False)
    print("Created sample_data/EU.xlsx")

    # 3. APAC Report (using "Test Case" and raw values)
    apac_data = {
        "Test Case": ["TC201", "TC202", "TC203"],
        "Status": ["NA", "Dependency", "Not Executed"],
        "Notes": ["No APAC scope", "Blocked by hardware shipment delay", "Not yet executed in sprint"]
    }
    pd.DataFrame(apac_data).to_excel("sample_data/APAC.xlsx", index=False)
    print("Created sample_data/APAC.xlsx")

    # 4. LATAM Report (no metadata column, standard headers but lowercase variations or similar)
    latam_data = {
        "Test_ID": ["TC301", "TC302", "TC303"],
        "Status": ["Pass", "Blocked", "NA"]
    }
    pd.DataFrame(latam_data).to_excel("sample_data/LATAM.xlsx", index=False)
    print("Created sample_data/LATAM.xlsx")

if __name__ == "__main__":
    create_sample_files()
