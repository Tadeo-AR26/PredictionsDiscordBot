import discord
from discord.ext import commands
import sqlite3
import requests
from io import BytesIO
from PIL import Image
from .utils import connect_db 
import config

intents = discord.Intents.all()
intents.message_content = True

def anadir_team():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    team = input("Team name: ")
    region = input("Region: ")
    image = input("Imagen: ")

    cursor.execute("INSERT INTO teams (name, region, image) VALUES (?, ?, ?)", (team, region, image)) # Insertar en la DB
    connection.commit() # Commitear los cambios
    connection.close()


def connect_db(db_name='database.db'):
    return sqlite3.connect(db_name)

@commands.command(name='register')
async def register(ctx, *, nombre: str = None):

    user_id = ctx.author.id

    if not nombre:
        await ctx.send("Ingrese un nombre junto al comando")
        return
    

    conn = connect_db('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT uid_discord FROM user WHERE uid_discord = ?', (user_id,))
    result = cursor.fetchone()

    if result:
        await ctx.send(f"Ya estás registrado")
    else:
        cursor.execute('INSERT INTO user (uid_discord, name) VALUES (?, ?)', (user_id, nombre))
        conn.commit()
        await ctx.send("Registrado")
    
    conn.close()