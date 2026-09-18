import zipfile
import sys

zip_path = r"C:\Users\HP\Downloads\_OREOLE ASSURANCE.zip"
try:
    with zipfile.ZipFile(zip_path, 'r') as z:
        for n in z.namelist():
            nl = n.lower()
            if any(k in nl for k in ['devis', 'auto', 'contrat']) and not n.endswith('/'):
                print(n)
except Exception as e:
    print("Error with _OREOLE ASSURANCE.zip:", e)

zip_path2 = r"C:\Users\HP\Downloads\OREOLE.zip"
try:
    with zipfile.ZipFile(zip_path2, 'r') as z:
        for n in z.namelist():
            nl = n.lower()
            if any(k in nl for k in ['devis', 'auto', 'contrat']) and not n.endswith('/'):
                print("OREOLE.zip:", n)
except Exception as e:
    print("Error with OREOLE.zip:", e)
