@echo off
setlocal EnableDelayedExpansion

call :find_home_test
if not defined HOME_TEST (
    echo No se encontro home_test.
    exit /b
)

echo Ruta: %HOME_TEST%
echo Permisos: %PERMISOS%

if /I "%PERMISOS%"=="true" (
    call :process_files "%HOME_TEST%"
)

exit /b

:find_home_test
set "HOME_TEST="
set "PERMISOS=false"

for /f "delims=" %%D in ('dir C:\ /ad /b /s 2^>nul ^| findstr /i "\\home_test$"') do (
    set "HOME_TEST=%%D"
    goto :check
)
exit /b

:check
set "PERMISOS=true"

for /r "%HOME_TEST%" %%F in (*) do (
    rem Intenta abrir el archivo
    type "%%F" >nul 2>nul || set "PERMISOS=false"
)

exit /b

:process_files
set "ROOT=%~1"

for /r "%ROOT%" %%F in (*) do (
    rem ============================
    rem Código para archivos
    rem ============================
    echo Archivo: %%F
)

for /d /r "%ROOT%" %%D in (*) do (
    rem ============================
    rem Código para carpetas
    rem ============================
    echo Directorio: %%D
)

exit /b