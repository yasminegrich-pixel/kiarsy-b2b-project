#!/usr/bin/env python3
import pandas as pd
import yaml
from pathlib import Path

DATA_DIR = Path.home() / "kiarsy" / "data"
EXCEL_FILE = DATA_DIR / "Kiarsy_Company_Database_v5.xlsx"

# Map your Excel's 11 values to our Universal 15
VALUE_MAP = {
    "Entrepreneurship & Innovation": "Entrepreneurship & Innovation",
    "Inclusivity & Opportunity": "Diversity, Inclusion & Minority Rights",
    "Women's Empowerment & Leadership": "Women's Empowerment & Gender Equity",
    "Collaboration & Long-Term Partnership": "Collaboration, Partnerships & Ecosystems",
    "Regional / Market Leadership": "Leadership, Governance & Authority",
    "Impact & Accountability": "Justice, Human Rights & Transparency",
    "Sustainability & Green Transition": "Environmental Sustainability & Climate Action",
    "Youth Development & Education": "Youth Development & Next-Gen Education",
    "Safety & Reliability": "Trust, Security & Risk Management",
    "Local Roots & Proximity": "Heritage, Craftsmanship & Legacy",
    "Movement / Momentum": "Transformation, Renewal & Change Management"
}

# Map the 'Tier' column to mathematical points
TIER_WEIGHTS = {
    "Explicit": 10,
    "Strongly Supported": 7,
    "Possible": 4
}

def main():
    print(f"📖 Reading {EXCEL_FILE.name}...")
    
    df_companies = pd.read_excel(EXCEL_FILE, sheet_name="Companies")
    df_values = pd.read_excel(EXCEL_FILE, sheet_name="Company Values")
    
    for _, row in df_companies.iterrows():
        cid = row["Company ID"]
        cname = row["Company Name"]
        
        # Create a clean filename (e.g., totalenergies_tunisie)
        clean_id = str(cname).lower().replace(" ", "_").replace("'", "")
        
        company_vals_df = df_values[df_values["Company ID"] == cid]
        if company_vals_df.empty:
            continue
            
        channel_1_values = {}
        for _, vrow in company_vals_df.iterrows():
            vname = vrow["Value Name"]
            tier = vrow["Tier"]
            
            if pd.isna(vname) or pd.isna(tier): continue
                
            universal_val = VALUE_MAP.get(vname)
            if not universal_val:
                print(f"  ⚠️  Unknown value '{vname}'")
                continue
                
            weight = TIER_WEIGHTS.get(tier, 5)
            channel_1_values[universal_val] = channel_1_values.get(universal_val, 0) + weight
            
        company_data = {
            'id': clean_id,
            'name': cname,
            'channel_1': {
                'source': 'Manual Research (Excel Import)',
                'values': channel_1_values
            }
        }
        
        out_file = DATA_DIR / "companies" / f"{clean_id}.yaml"
        with open(out_file, 'w') as f:
            yaml.dump(company_data, f, sort_keys=False)
            
        print(f"\n✅ Imported {cname} -> {out_file.name}")
        for v, w in sorted(channel_1_values.items(), key=lambda x: x[1], reverse=True):
            print(f"     [{w:>2} pts] {v}")

if __name__ == "__main__":
    main()
