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
echo  Step 2: Generate pages and update config
echo =========================================
python scripts/generate_pages.py

echo.
echo =========================================
echo  Step 3: Re-run SUSHI (with updated config)
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
echo  Step 5: IG Publisher
echo =========================================
java -jar input-cache/publisher.jar publisher -ig . -no-sushi

echo.
echo Done! Open output\index.html
pause