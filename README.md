venv\Scripts\activate
python -m venv venv
pip install -r requirements.txt
python app.py
pip freeze > requirements.txt
