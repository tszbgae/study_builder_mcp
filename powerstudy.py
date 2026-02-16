import csv
import time
import random
import os

# --- Configuration ---
executable = "/mnt/c/another.exe"

def model():
    """
    Generates inputs based on bounds and calculates mock outputs.
    """
    # 1. Generate Inputs (Random Uniform)
    power = random.uniform(1.0, 10.0)
    aero = random.uniform(10.0, 100.0)

    # 2. Calculate Outputs (Mock Functions)
    tastiness = (power + aero) * 1 * random.uniform(0.9, 1.1)
    cost = (power + aero) * 2 * random.uniform(0.9, 1.1)

    return {
        "power": power,
        "aero": aero,
        "tastiness": tastiness,
        "cost": cost
    }

if __name__ == "__main__":
    output_csv = "output.csv"
    headers = ['power', 'aero', 'tastiness', 'cost']
    
    print(f"Starting study run for executable: {executable}")
    print(f"Saving data to {output_csv}...")

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
            
        print(f"Step {i+1}/20: Written row.")
        
        # Wait 1 second
        time.sleep(1)

    print("Study complete.")
