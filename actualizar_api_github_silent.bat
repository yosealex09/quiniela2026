@echo off
cd /d C:\xampp\htdocs\quiniela

python actualizar_calendario_knockout.py >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1

python actualizar_api.py >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1
if errorlevel 1 exit /b 1

copy /Y datos.json "C:\Users\Yosember Rodriguez\datos.json" >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1
copy /Y index.html "C:\Users\Yosember Rodriguez\index.html" >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1
copy /Y calendario.json "C:\Users\Yosember Rodriguez\calendario.json" >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1

cd /d "C:\Users\Yosember Rodriguez"
git add datos.json index.html calendario.json >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1
git commit -m "Auto-actualizar resultados %date% %time%" >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1
git push >> "C:\xampp\htdocs\quiniela\logs\actualizar.log" 2>&1
