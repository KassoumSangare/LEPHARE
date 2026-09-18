import os

be_path = r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-backend'
for root, dirs, files in os.walk(be_path):
    for file in files:
        if file.endswith('.py'):
            fpath = os.path.join(root, file)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    data = f.read()
                    for term in ['voyage', 'transport', 'sante', 'mrh', 'habitation', 'individuelle']:
                        if term in data.lower() and ('devis' in data.lower() or 'quote' in data.lower() or 'tarif' in data.lower()):
                            print(f"{term} in {os.path.relpath(fpath, be_path)}")
                            break
            except Exception as e:
                pass
