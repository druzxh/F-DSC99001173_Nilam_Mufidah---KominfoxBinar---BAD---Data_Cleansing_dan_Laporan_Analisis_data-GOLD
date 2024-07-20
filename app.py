from flask import Flask, request, jsonify, redirect
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import pandas as pd
import os
import re
from sqlalchemy import create_engine, Column, Integer, String, Float, Table, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy
from utils import text_cleansing, text_processing, processing
import chardet

app = Flask(__name__)
DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db.sqlite3')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Pastikan direktori uploads ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

Base = declarative_base()
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
Session = sessionmaker(bind=engine)
session = Session()
metadata = MetaData()

dictionary_path = 'static/new_kamusalay.csv'
dictionary = pd.read_csv(dictionary_path, header=None, names=['slang', 'formal'], encoding='ISO-8859-1')

# Model untuk menyimpan teks asli dan teks yang telah dibersihkan
class TextClean(db.Model):
    __tablename__ = 'text_cleans'
    id = db.Column(db.Integer, primary_key=True)
    text_input = db.Column(db.String, nullable=False)
    text_clean = db.Column(db.String, nullable=False)

@app.route('/', methods=['GET'])
def route():
    return redirect('/api')

@app.route('/api/upload', methods=['POST'])
def upload_data():
    file = request.files.get('file')

    if not file:
        return jsonify({'error': 'No file provided'}), 400

    # Menyimpan file yang diupload
    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

# Baca file dalam mode biner dan deteksi encoding
    with open(file_path, 'rb') as f:
        raw_data = f.read()

    result = chardet.detect(raw_data)
    encoding = result['encoding']
    confidence = result['confidence']

    print(f'Detected encoding: {encoding} with confidence {confidence}')

    try:
        # Baca ulang file dengan encoding yang terdeteksi
        df = pd.read_csv(file_path, encoding=encoding)
    except UnicodeDecodeError as e:
        print(f'UnicodeDecodeError with detected encoding {encoding}: {e}')
        # Jika deteksi encoding gagal, coba beberapa encoding umum lainnya
        encodings_to_try = ['latin1', 'iso-8859-1', 'cp1252']
        for enc in encodings_to_try:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                break
            except UnicodeDecodeError as e:
                print(f'UnicodeDecodeError with fallback encoding {enc}: {e}')
                continue
        else:
            return jsonify({'error': 'File encoding not supported'}), 400


    # df = pd.read_csv(file_path)
    
    # Membersihkan teks di setiap kolom
    for column in df.columns:
        if df[column].dtype == object:  # Hanya membersihkan kolom yang bertipe objek (teks)
            # df[column] = df[column].apply(text_cleansing)
            # df[column] = df[column].apply(processing)
            df[column] = df[column].apply(lambda x: processing(x, dictionary))


    # Dynamically create a table based on the cleaned data
    table_name = os.path.splitext(filename)[0]  # Remove the .csv extension
    columns = [
        Column('id', Integer, primary_key=True)
    ]
    for column in df.columns:
        col_type = String if df[column].dtype == 'object' else Float
        columns.append(Column(column, col_type))

    dynamic_table = Table(table_name, metadata, *columns)
    metadata.create_all(engine)

    # Insert the cleaned data into the dynamic table
    df.to_sql(table_name, engine, if_exists='append', index=False)

    # Mengubah DataFrame menjadi list of dictionaries untuk dikirim dalam respons JSON
    cleaned_data = df.to_dict(orient='records')

    # Menyimpan data ke file CSV dengan nama baru
    cleaned_filename = filename.replace('.csv', '_clean.csv')
    cleaned_file_path = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_filename)
    df.to_csv(cleaned_file_path, index=False)

    # Hapus file yang diupload
    os.remove(file_path)

    return jsonify({'message': 'File uploaded and cleaned successfully'})

@app.route('/api/cleanse', methods=['POST'])
def cleanse_text():
    text = request.json.get('text')
    # data_text = text_cleansing(text)
    cleaned_text = processing(text, dictionary)
    
    # Menyimpan teks asli dan teks yang telah dibersihkan ke dalam tabel text_cleans
    new_text_clean = TextClean(text_input=text, text_clean=cleaned_text)
    db.session.add(new_text_clean)
    db.session.commit()
    
    return jsonify({'cleaned_text': cleaned_text})

# Setup Swagger UI
SWAGGER_URL = '/api'
API_URL = '/static/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Text dan Data Cleansing API"})
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
