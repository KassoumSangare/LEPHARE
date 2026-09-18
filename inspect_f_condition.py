with open(r'c:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

pos = code.find("0===parseInt(F)?")
print(code[pos:pos+4000])
