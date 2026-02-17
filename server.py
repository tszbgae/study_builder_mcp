from fastmcp import FastMCP
from typing import List, Dict, Optional
import json
import os
import csv
from pydantic import BaseModel, Field
import subprocess
import sys


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

def build_studypy(study_config: dict,output_script_name: str = "study.py") -> str:
    """
    Reads a study.json and generates a study.py runner script.
    """

    # Extract configuration
    exe_path = study_config.get("executable_path", "unknown_path")
    inputs = study_config.get("inputs", [])
    outputs = study_config.get("outputs", [])
    
    # 1. Prepare Input Logic (Random generation)
    # We build strings like: var_name = random.uniform(lower, upper)
    input_generators = []
    input_names = []
    for inp in inputs:
        name = inp["name"]
        low = inp["lower_bound"]
        high = inp["upper_bound"]
        input_generators.append(f"    {name} = random.uniform({low}, {high})")
        input_names.append(name)

    # 2. Prepare Output Logic (Mock functions)
    # We create dummy relationships so the data looks real.
    # Example: output = sum(inputs) + random_noise
    output_generators = []
    output_names = []
    
    # Create a string of all input variables to use in the mock formula
    sum_inputs_str = " + ".join(input_names) if input_names else "0"
    
    for i, out_name in enumerate(outputs):
        # We assign slightly different logic to each output so they aren't identical
        # output_1 = (sum of inputs) * (index + 1)
        output_generators.append(f"    {out_name} = ({sum_inputs_str}) * {i + 1} * random.uniform(0.9, 1.1)")
        output_names.append(out_name)

    # 3. Construct the Return Dictionary
    all_fields = input_names + output_names
    return_dict_lines = [f'        "{f}": {f}' for f in all_fields]
    return_dict_str = ",\n".join(return_dict_lines)

    # 4. Generate the full script content
    script_content = f"""import csv
import time
import random
import os

# --- Configuration ---
executable = "{exe_path}"

def model():
    \"\"\"
    Generates inputs based on bounds and calculates mock outputs.
    \"\"\"
    # 1. Generate Inputs (Random Uniform)
{chr(10).join(input_generators)}

    # 2. Calculate Outputs (Mock Functions)
{chr(10).join(output_generators)}

    return {{
{return_dict_str}
    }}

if __name__ == "__main__":
    output_csv = "output.csv"
    headers = {all_fields}
    
    print(f"Starting study run for executable: {{executable}}")
    print(f"Saving data to {{output_csv}}...")

    # Create CSV and write headers
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

    # Run for 20 seconds (1 iteration per second)
    for i in range(20):
        # Run the model
        data = model()
        
        # Append to CSV
        with open(output_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writerow(data)
            
        print(f"Step {{i+1}}/20: Written row.")
        
        # Wait 1 second
        time.sleep(1)

    print("Study complete.")
"""

    # Write the file
    with open(output_script_name, 'w') as f:
        f.write(script_content)

    return f"Successfully generated '{output_script_name}"

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

    
@mcp.tool()
def build_studypy_from_json(study_name: str, studypy_path: str) -> str:
    """
    Builds the study python file from the study json file
    """
    try:
        study = load_study(study_name)
        msg = build_studypy(study,studypy_path)
        return msg
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


@mcp.tool()
def run_study_script(script_path: str = "study.py") -> str:
    """
    Executes the study script in the BACKGROUND.
    Returns immediately with the Process ID (PID) so you can continue prompting.
    Output is redirected to 'study_execution.log'.
    """
    if not os.path.exists(script_path):
        return f"Error: Script '{script_path}' not found."

    try:
        # We open a log file so we don't lose the output
        log_file = open("study_execution.log", "w")

        # Popen starts the process non-blocking
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=log_file,
            stderr=subprocess.STDOUT, # Merge errors into the same log
            shell=False
        )
        
        # Note: We don't close log_file here immediately because the subprocess 
        # needs it open. It will be closed by the OS when the subprocess ends 
        # or we can rely on Python garbage collection to close the python handle eventually.
        # For a long-running server, it's safer to let the subprocess handle its own logging,
        # but for this utility, passing the file handle is the simplest method.
        
        return (f"Study started in background (PID: {process.pid}). "
                f"Output is being written to 'study_execution.log'. "
                f"You can now use 'get_study_progress' to monitor it.")

    except Exception as e:
        return f"Failed to start background process: {str(e)}"

@mcp.tool()
def get_study_progress(csv_path: str = "output.csv") -> str:
    """
    Checks the current progress of the study by counting rows in the output CSV.
    """
    if not os.path.exists(csv_path):
        return "Study has not started yet (output file not found)."
    
    try:
        with open(csv_path, 'r') as f:
            # Subtract 1 for header; if file is empty or just header, returns 0
            row_count = sum(1 for row in f) - 1
            
        if row_count < 0: row_count = 0
        return f"Current Progress: {row_count} iterations completed."
    except Exception as e:
        return f"Error reading progress: {str(e)}"
    
@mcp.tool()
def view_results_dashboard() -> str:
    """
    Launches a Streamlit dashboard to visualize the study results (output.csv).
    The dashboard will open in your default web browser (usually http://localhost:8501).
    """
    dashboard_script = "dashboard.py"
    
    if not os.path.exists(dashboard_script):
        # Allow the tool to create the file if it doesn't exist yet
        # (Self-correction mechanism)
        return "Error: dashboard.py not found. Please create the dashboard file first."

    try:
        # Launch Streamlit in the background
        # We redirect stdout/stderr to devnull to keep the console clean
        # You can access it at http://localhost:8501
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", dashboard_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        return "Dashboard launched successfully! You can view it at http://localhost:8501"
    except Exception as e:
        return f"Failed to launch dashboard: {str(e)}"
        
if __name__ == "__main__":
    mcp.run()