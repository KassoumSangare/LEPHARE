with open(r'c:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

pos = code.find("Y$=function")
print("Y$ (Flotte Vehicule component) pos:", pos)
if pos != -1:
    with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\flotte_step_code.js', 'w', encoding='utf-8') as out:
        out.write(code[pos:pos+25000])
    print("Written flotte_step_code.js")
