import csv
import time
import random
import os

# --- Configuration ---
executable = "/mnt/c/test.exe"

def model():
    """
    Generates inputs based on bounds and calculates mock outputs.
    """
    # 1. Generate Inputs (Random Uniform)
    speed = random.uniform(0.0, 5.5)
    agility = random.uniform(-10.0, 10.0)

    # 2. Calculate Outputs (Mock Functions)
    cost = (speed + agility) * 1 * random.uniform(0.9, 1.1)
    tastiness = (speed + agility) * 2 * random.uniform(0.9, 1.1)
    calories = (speed + agility) * 3 * random.uniform(0.9, 1.1)
    stability = (speed + agility) * 4 * random.uniform(0.9, 1.1)

    return {
        "speed": speed,
        "agility": agility,
        "cost": cost,
        "tastiness": tastiness,
        "calories": calories,
        "stability": stability
    }

if __name__ == "__main__":
    output_csv = "output.csv"
    headers = ['speed', 'agility', 'cost', 'tastiness', 'calories', 'stability']
    
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
