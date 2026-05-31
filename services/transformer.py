import pandas as pd
from typing import Dict, Any, List, Set

class DataTransformer:
    @staticmethod
    def transform(
        df: pd.DataFrame,
        col_mapping: Dict[str, str],
        value_mapping: Dict[str, Dict[str, str]],
        allowed_statuses: Set[str],
        region: str,
        execution_date: str,
        release: str,
        keep_all_columns: bool = False
    ) -> pd.DataFrame:
        """
        Apply mappings, value standardization, status filtering, and inject metadata columns.
        """
        # Create a deep copy to avoid modifying the original dataframe
        df_transformed = df.copy()

        # 1. Rename columns according to the mapped headers
        df_transformed = df_transformed.rename(columns=col_mapping)

        # Ensure schema columns exist or populate placeholders
        schema_defaults = {
            "Testcase ID": "Unknown",
            "Testcase Status": "Unknown",
            "Models": "",
            "Function": "",
            "Tester": "",
            "Comment": ""
        }
        for col, default_val in schema_defaults.items():
            if col not in df_transformed.columns:
                df_transformed[col] = default_val

        # 1.5 Filter by seq column if present (only keep rows where seq == 1)
        if "seq" in df_transformed.columns:
            df_transformed["seq_temp"] = df_transformed["seq"].astype(str).str.strip().str.replace(".0", "", regex=False)
            df_transformed = df_transformed[df_transformed["seq_temp"] == "1"]
            df_transformed = df_transformed.drop(columns=["seq_temp"])

        # 2. Standardize column values for Testcase Status
        status_value_map = value_mapping.get("Testcase Status", {})
        
        # Clean whitespaces and apply mapping
        df_transformed["Testcase Status"] = df_transformed["Testcase Status"].astype(str).str.strip()
        
        # We standardise via mapping dictionary, otherwise keep the cleaned raw value
        df_transformed["Testcase Status"] = df_transformed["Testcase Status"].apply(
            lambda val: status_value_map.get(val, val)
        )

        # 3. Filter rows based on target statuses (if allowed_statuses is provided)
        if allowed_statuses:
            df_transformed = df_transformed[df_transformed["Testcase Status"].isin(allowed_statuses)]

        # 4. Inject metadata columns
        df_transformed["Region"] = region

        # 5. Column selection: Keep only target columns + metadata columns unless keep_all_columns is True
        target_schema = ["Region", "Models", "Function", "Testcase ID", "Tester", "Testcase Status", "Comment"]
        if not keep_all_columns:
            # We filter down to exactly the target schema
            df_transformed = df_transformed[target_schema]
        else:
            # Move target columns to the front of the dataframe for readability
            all_cols = list(df_transformed.columns)
            for col in reversed(target_schema):
                if col in all_cols:
                    all_cols.remove(col)
                    all_cols.insert(0, col)
            df_transformed = df_transformed[all_cols]

        return df_transformed
