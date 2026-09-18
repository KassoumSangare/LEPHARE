with open(r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

pos = 2751355
print("=== CODE SUR LE FORMULAIRE DEVIS AUTOMOBILE (autour de 2751355) ===")
start = max(0, pos - 3000)
end = min(len(code), pos + 5000)

with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_code.js', 'w', encoding='utf-8') as out:
    out.write(code[start:end])

print("Written devis_auto_code.js, length:", end - start)
