#!/usr/bin/env python3
import csv
import yaml
from pathlib import Path

DATA_DIR = Path.home() / "kiarsy" / "data"
TESTS_DIR = DATA_DIR / "tests"

def main():
    # 1. Load the question mapping
    with open(TESTS_DIR / "question_mapping.yaml", 'r') as f:
        mapping = yaml.safe_load(f)

    # 2. Open the CSV
    csv_file = TESTS_DIR / "flat6labs_answers.csv"
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            company_name = row.get('Company', 'unknown').strip()
            company_id = company_name.lower().replace(" ", "_")
            
            channel_2_values = {}
            
            # 3. Process each question
            for question, answers_map in mapping.items():
                user_answer = row.get(question, "").strip()
                
                if user_answer in answers_map:
                    val = answers_map[user_answer]['value']
                    weight = answers_map[user_answer]['weight']
                    
                    channel_2_values[val] = channel_2_values.get(val, 0) + weight
                else:
                    print(f"Warning: Answer '{user_answer}' not in mapping.")

            # 4. Save to a YAML file in the format match.py expects
            output_data = {
                'id': company_id,
                'channel_2': {
                    'source': 'B2B Questionnaire Test',
                    'values': channel_2_values
                }
            }
            
            out_file = TESTS_DIR / f"{company_id}_test.yaml"
            with open(out_file, 'w') as f:
                yaml.dump(output_data, f, sort_keys=False)
                
            print(f"✅ Processed {company_name}. Saved to {out_file.name}")

if __name__ == "__main__":
    main()
