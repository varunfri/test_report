import pandas as pd
from typing import List
from services.logger import logger

class DataMerger:
    @staticmethod
    def merge(dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Consolidate a list of transformed regional DataFrames into a single clean DataFrame.
        """
        logger.info(f"Merging {len(dfs)} regional dataframes...")
        if not dfs:
            logger.warning("No dataframes provided to merge. Returning empty standard dataframe.")
            return pd.DataFrame(columns=["Region", "Module", "Function", "Testcase ID", "Tester", "Testcase Status", "Comment"])
        
        # Concatenate and reset index
        merged_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Merged successfully. Total consolidated rows: {len(merged_df)}")
        return merged_df
