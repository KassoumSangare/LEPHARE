import re

def inspect_file(fpath, label):
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        print(f"=== {label} ({len(lines)} lines) ===")
        for i, line in enumerate(lines):
            if any(term in line.lower() for term in ['def calcul', 'def enregistre', 'def devis', 'def sp_', 'class devis', 'path(']):
                print(f"  Line {i+1}: {line.strip()[:100]}")
    except Exception as e:
        print(f"Error {label}: {e}")

be_path = r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-backend'
inspect_file(f"{be_path}\\production\\services\\mrh_calcul_service.py", "MRH Service")
inspect_file(f"{be_path}\\sante\\views.py", "Sante Views")
inspect_file(f"{be_path}\\sante\\urls.py", "Sante URLs")
