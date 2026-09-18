with open(r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

pos = 2859647 # Where function o$ (vehicule step) is declared!
start = max(0, pos - 1000)
end = min(len(code), pos + 25000)

with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'w', encoding='utf-8') as out:
    out.write(code[start:end])

print("Written vehicule_step_code.js, length:", end - start)
