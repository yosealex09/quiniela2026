@echo off
echo ========================================
echo   Quiniela Mundial 2026 - Actualizando (API)
echo ========================================
echo.

cd /d C:\xampp\htdocs\quiniela

echo [1/4] Resolviendo cruces de eliminatoria confirmados...
python actualizar_calendario_knockout.py

echo.
echo [2/4] Descargando resultados reales y generando datos.json...
python actualizar_api.py
if errorlevel 1 (
    echo ERROR: Fallo el script de actualizacion.
    pause
    exit /b 1
)

echo.
echo [3/4] Copiando datos.json, index.html y calendario.json al repositorio...
copy /Y datos.json "C:\Users\Yosember Rodriguez\datos.json"
copy /Y index.html "C:\Users\Yosember Rodriguez\index.html"
copy /Y calendario.json "C:\Users\Yosember Rodriguez\calendario.json"

echo.
echo [4/4] Subiendo a GitHub...
cd /d "C:\Users\Yosember Rodriguez"
git add datos.json index.html calendario.json
git commit -m "Actualizar resultados (API) %date% %time%"
git push

echo.
echo ========================================
echo   Listo! Pagina actualizada en GitHub
echo   https://yosealex09.github.io/quiniela2026
echo ========================================
pause
