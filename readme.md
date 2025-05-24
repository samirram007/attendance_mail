set FLASK_APP=wsgi.py        # Windows CMD
$env:FLASK_APP="wsgi.py"     # PowerShell
export FLASK_APP=wsgi.py     # Linux/macOS

flask run

or

gunicorn --bind 0.0.0.0:5001 wsgi:app

python -m waitress --host=0.0.0.0 --port=5001 wsgi:app

###

python -m venv venv310
.venv\Scripts\activate

rm -rf venv310
python -m venv venv310
source .venv/bin/activate

py run.py
pip install -r requirements.txt
pip freeze > requirements.txt

pip install flask

flask --app myapp init-db
pip install -e .



sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl start attendance
sudo systemctl enable attendance


sudo apt update
sudo apt install wkhtmltopdf
# or for latest version:
# sudo snap install wkhtmltopdf