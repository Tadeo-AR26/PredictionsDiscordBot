import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import sqlite3
import requests
from io import BytesIO
from PIL import Image
from itertools import cycle
import asyncio
from functions import administration, predictModule
from functions.administration import register
from functions.predictModule import *
import config

intents = discord.Intents.all()
intents.message_content = True

# Cargar variables de entorno desde el archivo .env
load_dotenv('enviroment.env')
TOKEN = os.getenv('DISCORD_TOKEN')

config.bot = commands.Bot(command_prefix='!', intents=intents)

config.bot.add_command(register)
config.bot.add_command(mostrar_match)
config.bot.add_command(predecir)
config.bot.add_command(points)
config.bot.add_command(result)
config.bot.add_command(leaderboard)


config.bot.run(TOKEN)