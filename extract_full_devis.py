with open(r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

pos = 2751355
start = max(0, pos - 15000)
end = min(len(code), pos + 35000)

with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_full.js', 'w', encoding='utf-8') as out:
    out.write(code[start:end])

print("Written devis_auto_full.js, size:", end - start)
