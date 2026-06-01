import pandas as pd
from typing import List, Union, Dict, Any, IO
from services.logger import logger

class FileLoader:
    @staticmethod
    def get_sheet_names(file_src: Union[str, IO[bytes]]) -> List[str]:
        """
        Extract sheet names from an Excel file source.
        """
        try:
            filename = getattr(file_src, 'name', 'BytesIOStream')
            logger.info(f"Extracting sheet names from file: {filename}")
            xls = pd.ExcelFile(file_src)
            sheets = xls.sheet_names
            logger.info(f"Found sheets: {sheets}")
            return sheets
        except Exception as e:
            logger.error(f"Failed to read sheets: {str(e)}")
            raise ValueError(f"Failed to read sheets from Excel file: {str(e)}")

    @staticmethod
    def load_sheet(file_src: Union[str, IO[bytes]], sheet_name: str = None) -> pd.DataFrame:
        """
        Load a sheet from an Excel file source into a Pandas DataFrame.
        Cleans column names by stripping whitespaces.
        """
        try:
            filename = getattr(file_src, 'name', 'BytesIOStream')
            logger.info(f"Loading sheet '{sheet_name}' from file: {filename}")
            if sheet_name is None:
                # Load first sheet
                df = pd.read_excel(file_src, keep_default_na=False)
            else:
                df = pd.read_excel(file_src, sheet_name=sheet_name, keep_default_na=False)
            
            # Clean column headers
            df.columns = [str(col).strip() for col in df.columns]
            logger.info(f"Loaded {len(df)} rows. Columns: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Failed to load sheet '{sheet_name}': {str(e)}")
            raise ValueError(f"Failed to load sheet '{sheet_name}': {str(e)}")
