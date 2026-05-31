import pandas as pd
from typing import List

class DataMerger:
    @staticmethod
    def merge(dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Consolidate a list of transformed regional DataFrames into a single clean DataFrame.
        """
        if not dfs:
            return pd.DataFrame(columns=["Region", "Models", "Function", "Testcase ID", "Tester", "Testcase Status", "Comment"])
        
        # Concatenate and reset index
        merged_df = pd.concat(dfs, ignore_index=True)
        return merged_df
