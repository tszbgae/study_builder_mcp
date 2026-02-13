from fastmcp import FastMCP
from typing import List, Dict, Optional
import json
import os
import csv
from pydantic import BaseModel, Field

# Initialize the server
mcp = FastMCP("StudyBuilder")

# --- Constants & Helpers ---
STUDY_DIR = "study_jsons"
os.makedirs(STUDY_DIR, exist_ok=True)

def get_study_path(study_name: str) -> str:
    """Returns the full path for a study JSON file."""
    # Ensure filename is safe and ends in .json
    safe_name = "".join([c for c in study_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    return os.path.join(STUDY_DIR, f"{safe_name}.json")

def load_study(study_name: str) -> Dict:
    """Loads the study JSON or returns a skeleton if it doesn't exist."""
    path = get_study_path(study_name)
    if not os.path.exists(path):
        return {
            "study_name": study_name,
            "executable_path": "",
            "inputs": [],
            "outputs": []
        }
    with open(path, 'r') as f:
        return json.load(f)

def save_study(study_data: Dict) -> str:
    """Saves the study dictionary to JSON."""
    path = get_study_path(study_data["study_name"])
    with open(path, 'w') as f:
        json.dump(study_data, f, indent=4)
    return f"Study saved successfully to {path}"

# --- Tools ---

@mcp.tool()
def create_or_load_study(study_name: str) -> str:
    """
    Initializes a new study or loads an existing one. 
    Always call this first to ensure the file exists.
    """
    study = load_study(study_name)
    save_study(study)
    return f"Study '{study_name}' is active. Current state: {json.dumps(study, indent=2)}"

@mcp.tool()
def set_executable_path(study_name: str, path: str) -> str:
    """
    Sets the 'executable_path' for the study. 
    The path must be a string pointing to an executable file.
    """
    study = load_study(study_name)
    study["executable_path"] = path
    save_study(study)
    return f"Executable path set to: {path}"

@mcp.tool()
def add_input_manual(study_name: str, name: str, lower_bound: float, upper_bound: float) -> str:
    """
    Adds a single input definition to the study manually.
    """
    study = load_study(study_name)
    
    # Check if input already exists and update it, or append new
    existing = next((item for item in study["inputs"] if item["name"] == name), None)
    new_input = {"name": name, "lower_bound": lower_bound, "upper_bound": upper_bound}
    
    if existing:
        study["inputs"].remove(existing)
        study["inputs"].append(new_input)
        msg = f"Updated existing input '{name}'."
    else:
        study["inputs"].append(new_input)
        msg = f"Added new input '{name}'."
        
    save_study(study)
    return msg

@mcp.tool()
def add_inputs_from_csv(study_name: str, csv_path: str) -> str:
    """
    Reads inputs from a CSV file.
    The CSV MUST have headers: 'name', 'lower_bound', 'upper_bound'.
    """
    if not os.path.exists(csv_path):
        return f"Error: CSV file not found at {csv_path}"

    study = load_study(study_name)
    count = 0
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            # Normalize headers (strip whitespace/lowercase) for robustness
            headers = [h.strip() for h in reader.fieldnames]
            required = {'name', 'lower_bound', 'upper_bound'}
            
            if not required.issubset(set(headers)):
                return f"Error: CSV missing required headers. Found: {headers}. Required: {required}"

            for row in reader:
                try:
                    new_input = {
                        "name": row["name"],
                        "lower_bound": float(row["lower_bound"]),
                        "upper_bound": float(row["upper_bound"])
                    }
                    study["inputs"].append(new_input)
                    count += 1
                except ValueError:
                    return f"Error parsing row {row}. Bounds must be numbers."
                    
        save_study(study)
        return f"Successfully imported {count} inputs from CSV."
        
    except Exception as e:
        return f"Error processing CSV: {str(e)}"

@mcp.tool()
def read_available_outputs_from_file(filepath: str) -> str:
    """
    Step 1 of getting outputs: Reads a .txt file where each line is an output name.
    Returns the list of found outputs so the user can select which ones they want.
    """
    if not os.path.exists(filepath):
        return f"Error: File not found at {filepath}"
    
    try:
        with open(filepath, 'r') as f:
            # Read lines and strip whitespace
            outputs = [line.strip() for line in f.readlines() if line.strip()]
        
        return f"Found the following outputs in file:\n" + "\n".join(outputs) + "\n\nPlease ask the user which of these they would like to add to the study."
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def set_study_outputs(study_name: str, selected_outputs: List[str]) -> str:
    """
    Step 2 of getting outputs: Saves the list of user-selected output strings to the study.
    """
    study = load_study(study_name)
    # Avoid duplicates
    current_outputs = set(study["outputs"])
    current_outputs.update(selected_outputs)
    study["outputs"] = list(current_outputs)
    
    save_study(study)
    return f"Updated study outputs. Current list: {study['outputs']}"

@mcp.tool()
def get_study_status(study_name: str) -> str:
    """
    Analyzes the study JSON and reports what is valid and what is missing.
    """
    study = load_study(study_name)
    
    report = []
    report.append(f"--- Status for Study: {study_name} ---")
    
    # Check Executable
    if study.get("executable_path"):
        report.append(f"[OK] Executable path set: {study['executable_path']}")
    else:
        report.append(f"[MISSING] Executable path is empty.")
        
    # Check Inputs
    inputs = study.get("inputs", [])
    if inputs:
        report.append(f"[OK] {len(inputs)} Inputs defined.")
    else:
        report.append(f"[MISSING] No inputs defined.")

    # Check Outputs
    outputs = study.get("outputs", [])
    if outputs:
        report.append(f"[OK] {len(outputs)} Outputs defined: {', '.join(outputs)}")
    else:
        report.append(f"[MISSING] No outputs defined.")

    # Validation verdict
    if study.get("executable_path") and inputs and outputs:
        report.append("\nRESULT: Study is VALID and ready.")
    else:
        report.append("\nRESULT: Study is INCOMPLETE.")
        
    return "\n".join(report)

if __name__ == "__main__":
    mcp.run()