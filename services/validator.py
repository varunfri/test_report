import pandas as pd
from typing import Dict, Any, List, Set
from services.logger import logger

class DataValidator:
    def __init__(self, target_columns: List[str] = None):
        # Default mandatory columns we need after mapping
        self.target_columns = target_columns or ["Testcase ID", "Testcase Status"]

    def validate(self, df: pd.DataFrame, col_mapping: Dict[str, str], allowed_statuses: Set[str]) -> Dict[str, Any]:
        """
        Validate a loaded DataFrame before transformation.
        Returns a dictionary representing the validation report.
        """
        logger.info(f"Running data validation on sheet with {len(df)} rows.")
        report = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "duplicate_columns": [],
            "missing_expected_columns": [],
            "unknown_statuses": [],
            "row_count": len(df)
        }

        # 1. Check if empty
        if df.empty:
            report["is_valid"] = False
            report["errors"].append("The Excel file sheet contains no data.")
            logger.error("Validation error: Sheet is empty.")
            return report

        # 2. Check for duplicate columns in raw file
        raw_cols = list(df.columns)
        if len(raw_cols) != len(set(raw_cols)):
            duplicates = set([c for c in raw_cols if raw_cols.count(c) > 1])
            report["duplicate_columns"] = list(duplicates)
            msg = f"Duplicate columns detected in input file: {', '.join(duplicates)}"
            report["warnings"].append(msg)
            logger.warning(f"Validation warning: {msg}")

        # 3. Identify mapped columns and find missing target columns
        mapped_targets = set()
        active_mappings = {}
        for col in df.columns:
            if col in col_mapping:
                target_col = col_mapping[col]
                mapped_targets.add(target_col)
                active_mappings[col] = target_col

        missing_targets = [col for col in self.target_columns if col not in mapped_targets]
        if missing_targets:
            report["is_valid"] = False
            report["missing_expected_columns"] = missing_targets
            msg = f"Missing required columns. Could not resolve mappings for: {', '.join(missing_targets)}"
            report["errors"].append(msg)
            logger.error(f"Validation error: {msg}")

        # 4. Check for unknown/unstandardized statuses if 'Testcase Status' column can be resolved
        status_col = None
        for col, target in active_mappings.items():
            if target == "Testcase Status":
                status_col = col
                break

        if status_col:
            raw_statuses = df[status_col].dropna().unique()
            unknown_vals = []
            for status in raw_statuses:
                status_str = str(status).strip()
                if status_str not in allowed_statuses:
                    unknown_vals.append(status_str)
            
            if unknown_vals:
                report["unknown_statuses"] = unknown_vals
                msg = f"Found unstandardized or raw statuses: {', '.join(unknown_vals)}"
                report["warnings"].append(msg)
                logger.warning(f"Validation warning: {msg}")

        logger.info(f"Validation completed. Is valid: {report['is_valid']}. Errors: {len(report['errors'])}, Warnings: {len(report['warnings'])}")
        return report
