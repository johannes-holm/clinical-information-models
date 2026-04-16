@echo off

echo =========================================
echo  Step 1: SUSHI (discover models)
echo =========================================
call sushi .
if %errorlevel% neq 0 (
    echo SUSHI failed!
    pause
    exit /b 1
)

echo.
echo =========================================
echo  Step 2: Generate pages and config
echo =========================================
python scripts/generate_pages.py

echo.
echo =========================================
echo  Step 3: Re-run SUSHI (updated config)
echo =========================================
call sushi .

echo.
echo =========================================
echo  Step 4: Generate diagrams and tables
echo =========================================
python scripts/generate_mermaid.py
python scripts/generate_table.py

echo.
echo =========================================
echo  Step 5: Render Mermaid to SVG
echo =========================================
where mmdc >nul 2>nul
if %errorlevel% equ 0 (
    for %%f in (input\images\generated\*.mmd) do (
        echo Rendering: %%f
        call mmdc -i "%%f" -o "%%~dpnf.svg" -t neutral --quiet
    )
) else (
    echo WARNING: mmdc not found. Install: npm install -g @mermaid-js/mermaid-cli
    echo Diagrams will show as broken images.
)

echo.
echo =========================================
echo  Step 6: IG Publisher
echo =========================================
java -jar input-cache/publisher.jar publisher -ig .

echo.
echo Done! Open output\index.html
pause