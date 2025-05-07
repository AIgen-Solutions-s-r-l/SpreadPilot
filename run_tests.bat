@echo off
echo Activating virtual environment...
call .\venv\Scripts\activate.bat

echo Running pytest...
python -m pytest

echo Deactivating virtual environment...
call deactivate

echo Done.