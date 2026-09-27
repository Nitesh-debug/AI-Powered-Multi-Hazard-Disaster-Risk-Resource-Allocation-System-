import sys
import os
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from agents.resource_agent import ResourceAgent

def test_risk_probability():
    agent = ResourceAgent()
    
    # Run allocation which generates predictions
    # We use historical data (non-live) to be deterministic-ish, or just run it.
    # The default run_allocation uses live if available, else CSV.
    result = agent.run_allocation(use_live=False)
    
    if result.get("type") == "error":
        print("Error running allocation:", result.get("response_text"))
        return

    # Check the latest prediction file
    results_dir = os.path.join(os.getcwd(), "results")
    pred_files = sorted([f for f in os.listdir(results_dir) if f.startswith("predictions") and f.endswith(".csv")])
    if not pred_files:
        print("No prediction file generated.")
        return
        
    latest_file = os.path.join(results_dir, pred_files[-1])
    print(f"Reading {latest_file}...")
    
    df = pd.read_csv(latest_file)
    print("\nSample Data (District, Risk Level, Risk Probability):")
    print(df[['district', 'risk_level', 'risk_probability']].head(10))
    
    # Verification Logic
    # For Risk Level 0, Risk Probability should be low (e.g. < 0.5)
    # For Risk Level > 0, Risk Probability should be high (e.g. > 0.5) 
    # (Strictly speaking, it depends on the distribution, but usually 0 is dominant)
    
    safe_districts = df[df['risk_level'] == 0]
    risky_districts = df[df['risk_level'] > 0]
    
    print("\n--- Statistics ---")
    if not safe_districts.empty:
        max_safe_prob = safe_districts['risk_probability'].max()
        print(f"Max Risk Probability for Safe Districts: {max_safe_prob} (Should be low)")
    
    if not risky_districts.empty:
        min_risky_prob = risky_districts['risk_probability'].min()
        print(f"Min Risk Probability for Risky Districts: {min_risky_prob} (Should be high)")

if __name__ == "__main__":
    test_risk_probability()
