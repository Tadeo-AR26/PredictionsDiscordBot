import sqlite3
import requests
from io import BytesIO
from PIL import Image

def connect_db(db_name='database.db'):
    return sqlite3.connect(db_name)

def combine_images_horizontal(img1_bytes, img2_bytes, width=1000, height=1200):
    # Abre las imágenes desde flujos de bytes
    img1 = Image.open(BytesIO(img1_bytes))
    img2 = Image.open(BytesIO(img2_bytes))

    # Redimensionar las imágenes manteniendo la misma altura
    img1 = img1.resize((width // 2, height // 2), Image.LANCZOS)
    img2 = img2.resize((width // 2, height // 2), Image.LANCZOS)

    # Crear una nueva imagen con el tamaño fijo
    new_img = Image.new('RGBA', (width + 30, height // 2), (255, 255, 255, 0))  # Fondo transparente

    # Pegar las imágenes en la nueva imagen
    new_img.paste(img1, (0, 0))
    new_img.paste(img2, ((width // 2) + 29, 0))

    # Guarda la nueva imagen en un objeto de bytes
    with BytesIO() as output:
        new_img.save(output, format='PNG')  # Guardar como PNG
        return output.getvalue()

def get_team_data(cursor, team_id):
    cursor.execute('SELECT name, image FROM teams WHERE id = ?', (team_id,))
    return cursor.fetchone()

def fetch_and_combine_images(imageurl1, imageurl2):
    response1 = requests.get(imageurl1)
    response2 = requests.get(imageurl2)

    return combine_images_horizontal(response1.content, response2.content)

def fetch_match_data_by_id(cursor, match_id):
    cursor.execute('SELECT team1, team2, team1_result, team2_result FROM match WHERE id_match = ?', (match_id,))
    return cursor.fetchone()

def fetch_matches_by_team(cursor, team_name):
    cursor.execute('''
        SELECT m.id_match, t1.name, t2.name, m.team1_result, m.team2_result
        FROM match m
        JOIN teams t1 ON m.team1 = t1.id
        JOIN teams t2 ON m.team2 = t2.id
        WHERE t1.name = ? OR t2.name = ?
    ''', (team_name, team_name))
    return cursor.fetchall()

def save_prediction(cursor, user_id, match_id, team1_result, team2_result):
    cursor.execute('''
        SELECT * FROM prediction
        WHERE user = ? AND match = ?
    ''', (user_id, match_id))
    prediction_row = cursor.fetchone()

    if prediction_row:
        if prediction_row[4] != 1:  # Suponiendo que la columna 'flag' es la quinta en el resultado (índice 4)
            cursor.execute('''
                UPDATE prediction
                SET team1_result = ?, team2_result = ?
                WHERE user = ? AND match = ?
            ''', (team1_result, team2_result, user_id, match_id))
    else:
        cursor.execute('''
            INSERT INTO prediction (user, match, team1_result, team2_result, flag)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, match_id, team1_result, team2_result, 0))
