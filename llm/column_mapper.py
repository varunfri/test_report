import requests
import json
from typing import List, Dict, Any, Tuple

class OllamaMapper:
    def __init__(self, host: str = "http://localhost:11434", default_model: str = "llama3"):
        self.host = host.rstrip("/")
        self.default_model = default_model

    def check_connection(self) -> Tuple[bool, List[str]]:
        """
        Check if Ollama is running and retrieve list of available models.
        Returns a tuple of (is_connected, available_models).
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return True, models
            return False, []
        except Exception:
            return False, []

    def get_column_mappings(
        self,
        source_cols: List[str],
        target_cols: List[str],
        model: str = None
    ) -> Dict[str, str]:
        """
        Prompts Ollama to map raw spreadsheet columns to the standardized target columns.
        Uses JSON mode to guarantee a clean structured response.
        """
        model_name = model or self.default_model
        
        prompt = f"""
You are an expert data migration assistant. Your task is to match raw Excel column names to a standardized schema.

Target Columns: {json.dumps(target_cols)}
Uploaded Columns: {json.dumps(source_cols)}

Instruction:
Create a mapping from the Uploaded Columns to the most appropriate Target Columns.
Only map columns that clearly match a target column. If a column has no matching target, do not include it.

Provide your output as a single JSON object where:
- Keys are the exact source column names from the Uploaded Columns list.
- Values are the matching column names from the Target Columns list.

Example response:
{{
  "TC_ID": "Testcase ID",
  "Status_Code": "Testcase Status"
}}

Respond ONLY with valid JSON.
"""
        
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.0
                    }
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "").strip()
                mappings = json.loads(content)
                
                # Clean and filter mapping to ensure only valid targets are mapped
                validated_mappings = {}
                for src, tgt in mappings.items():
                    if src in source_cols and tgt in target_cols:
                        validated_mappings[src] = tgt
                return validated_mappings
                
            return {}
        except Exception as e:
            # Silent fallback, calling service can handle logging/warnings
            return {}

    def get_status_mappings(
        self,
        raw_statuses: List[str],
        standard_statuses: List[str],
        model: str = None
    ) -> Dict[str, str]:
        """
        Prompts Ollama to map raw/unstandardized status values to the target allowed statuses.
        Uses JSON mode.
        """
        model_name = model or self.default_model
        
        prompt = f"""
You are a data validation assistant. Your task is to map unstandardized spreadsheet cell values to a list of allowed standard statuses.

Allowed Standard Statuses: {json.dumps(standard_statuses)}
Raw/Uploaded Status Values: {json.dumps(raw_statuses)}

Instruction:
For each raw status value, identify which standard status it corresponds to.
- For example, "BLKD", "Blocked", "Dependency" might map to "Blocked".
- "N/A", "NA", "Not Applicable" might map to "NA".
- If a raw status doesn't fit any standard status (like "Pass" or "Fail" when target is only NA/Blocked), do NOT map it or map it to null/empty string.

Provide your output as a single JSON object where:
- Keys are the exact raw status values.
- Values are the matching standard status names.

Respond ONLY with valid JSON.
"""

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.0
                    }
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "").strip()
                mappings = json.loads(content)
                
                # Filter only valid mappings
                validated_mappings = {}
                for src, tgt in mappings.items():
                    if tgt in standard_statuses:
                        validated_mappings[str(src)] = tgt
                return validated_mappings
                
            return {}
        except Exception:
            return {}
