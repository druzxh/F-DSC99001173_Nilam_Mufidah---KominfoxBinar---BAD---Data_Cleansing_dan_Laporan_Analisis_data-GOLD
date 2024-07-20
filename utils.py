import pandas as pd
import re

dictionary_path = 'static/new_kamusalay.csv'
dictionary = pd.read_csv(dictionary_path, header=None, names=['slang', 'formal'], encoding='ISO-8859-1')
def text_cleansing(text):
    cleaned_text = re.sub(r'[^a-zA-Z\s]', '', text)  # Hanya menyisakan huruf, angka, dan spasi
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Mengganti spasi berlebih dengan satu spasi
    cleaned_text = cleaned_text.strip()  # Menghapus spasi di awal dan akhir teks
    return cleaned_text

def text_processing(text, dictionary):
    for _, row in dictionary.iterrows():
        slang = row['slang']
        formal = row['formal']
        text = re.sub(r'\b{}\b'.format(re.escape(slang)), formal, text, flags=re.IGNORECASE)
    return text

def processing(text, dictionary):
    text = text_cleansing(text)
    # text = text_processing(text, dictionary)
    return text
