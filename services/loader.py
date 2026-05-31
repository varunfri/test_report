import pandas as pd
from typing import List, Union, Dict, Any, IO

class FileLoader:
    @staticmethod
    def get_sheet_names(file_src: Union[str, IO[bytes]]) -> List[str]:
        """
        Extract sheet names from an Excel file source.
        """
        try:
            xls = pd.ExcelFile(file_src)
            return xls.sheet_names
        except Exception as e:
            raise ValueError(f"Failed to read sheets from Excel file: {str(e)}")

    @staticmethod
    def load_sheet(file_src: Union[str, IO[bytes]], sheet_name: str = None) -> pd.DataFrame:
        """
        Load a sheet from an Excel file source into a Pandas DataFrame.
        Cleans column names by stripping whitespaces.
        """
        try:
            if sheet_name is None:
                # Load first sheet
                df = pd.read_excel(file_src, keep_default_na=False)
            else:
                df = pd.read_excel(file_src, sheet_name=sheet_name, keep_default_na=False)
            
            # Clean column headers
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e:
            raise ValueError(f"Failed to load sheet '{sheet_name}': {str(e)}")
