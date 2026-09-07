import psycopg2
import openpyxl
import re

FILES = {
    'amazigh': '/home/yasso/Downloads/amazigh_culture_symbols_common_meanings_rewritten.xlsx',
    'amerindienne': '/home/yasso/Downloads/indigenous_american_culture_symbols_common_meanings_rewritten.xlsx',
    'subsaharienne': '/home/yasso/Downloads/subsaharan_culture_symbols_common_meanings.xlsx'
}

SHEET_NAME = 'Verified Symbol Library'

def get_col_indices(header):
    return {name: i for i, name in enumerate(header)}

def determine_usage_status(sensitivity_notes):
    if not sensitivity_notes:
        return 'open'
    notes_lower = sensitivity_notes.lower()
    # Flag as restricted if it mentions sacred, ceremonial, legal, or specific protected items
    strict_keywords = ['sacred', 'ceremonial', 'reserved for', 'legal', 'eagle feather', 
                       'katsina', 'kachina', 'regalia', 'do not use', 'do not reproduce']
    for kw in strict_keywords:
        if kw in notes_lower:
            return 'restricted'
    return 'open'

def main():
    print("🔌 Connecting to database...")
    conn = psycopg2.connect(dbname="kiarsy_affinity", user="yasso")
    cur = conn.cursor()

    print("🧹 Clearing old test symbols and their scores...")
    cur.execute("DELETE FROM company_symbol_affinity;")
    cur.execute("DELETE FROM symbol_dimension_scores;")
    cur.execute("DELETE FROM symbol_value_matches;")
    cur.execute("DELETE FROM symbols;")
    conn.commit()

    print("🏗️  Adding new rich columns to symbols table...")
    alter_sql = """
    ALTER TABLE symbols 
      ADD COLUMN IF NOT EXISTS sub_culture text,
      ADD COLUMN IF NOT EXISTS timeframe text,
      ADD COLUMN IF NOT EXISTS region text,
      ADD COLUMN IF NOT EXISTS country text,
      ADD COLUMN IF NOT EXISTS motif_type text,
      ADD COLUMN IF NOT EXISTS usage_context text,
      ADD COLUMN IF NOT EXISTS historical_context text,
      ADD COLUMN IF NOT EXISTS primary_emotion text,
      ADD COLUMN IF NOT EXISTS colors_patterns text,
      ADD COLUMN IF NOT EXISTS cross_check_notes text,
      ADD COLUMN IF NOT EXISTS source_url text;
    """
    cur.execute(alter_sql)
    conn.commit()

    total_imported = 0
    
    for culture_id, filepath in FILES.items():
        print(f"\n📖 Processing {culture_id} from {filepath.split('/')[-1]}...")
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        if SHEET_NAME not in wb.sheetnames:
            print(f"  ⚠️ Sheet '{SHEET_NAME}' not found. Skipping.")
            continue
            
        ws = wb[SHEET_NAME]
        rows = list(ws.rows)
        if not rows: continue
        
        header = [cell.value for cell in rows[0]]
        idx = get_col_indices(header)
        
        def get_val(row, col_name):
            i = idx.get(col_name)
            if i is not None and row[i].value is not None:
                return str(row[i].value).strip()
            return None

        count = 0
        for row in rows[1:]:
            sym_id = get_val(row, 'Symbol ID')
            if not sym_id or sym_id.startswith('Symbol ID'): continue
            
            name = get_val(row, 'Symbol Name')
            meaning = get_val(row, 'Common Meaning')
            
            if not name or not meaning:
                continue
                
            sources = get_val(row, 'Source Name')
            source_url = get_val(row, 'Source URL')
            confidence = get_val(row, 'Confidence Level')
            sensitivity = get_val(row, 'Cultural Sensitivity / Usage Notes')
            
            # skip unsourced rows
            if confidence and 'needs' in confidence.lower():
                continue
            ver_level = 'verified'
            if confidence and 'caveat' in confidence.lower():
                ver_level = 'verified_candidate'
            elif confidence and 'needs' in confidence.lower():
                ver_level = 'probable'
                
            usage_status = determine_usage_status(sensitivity)
            
            insert_sql = """
            INSERT INTO symbols (
                symbol_id, symbol_name, culture_id, documented_meaning, sources, 
                verification_level, usage_status, usage_note,
                sub_culture, timeframe, region, country, motif_type, usage_context,
                historical_context, primary_emotion, colors_patterns, cross_check_notes, source_url
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (symbol_id) DO NOTHING
            """
            
            cur.execute(insert_sql, (
                sym_id, name, culture_id, meaning, sources, ver_level, usage_status, sensitivity,
                get_val(row, 'Sub-culture'), get_val(row, 'Timeframe'), get_val(row, 'Region'), 
                get_val(row, 'Country'), get_val(row, 'Motif Type'), get_val(row, 'Usage Context'),
                get_val(row, 'Historical Context'), get_val(row, 'Primary Emotion'), 
                get_val(row, 'Colors / Patterns'), get_val(row, 'Cross-check Notes'), source_url
            ))
            count += 1
            
        wb.close()
        print(f"  ✅ Imported {count} verified symbols for {culture_id}.")
        total_imported += count

    conn.commit()
    
    print("\n--- FINAL LIBRARY COUNTS ---")
    cur.execute("SELECT culture_id, count(*) FROM symbols GROUP BY culture_id ORDER BY culture_id;")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} symbols")
        
    cur.execute("SELECT count(*) FROM symbols WHERE usage_status = 'restricted';")
    res_count = cur.fetchone()[0]
    print(f"\n⚠️  {res_count} symbols flagged as 'restricted' (sacred/ceremonial/legal).")
    
    cur.close()
    conn.close()
    print("\n🎉 Import complete! Ready to re-run the scorer.")

if __name__ == "__main__":
    main()
