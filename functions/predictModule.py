import discord
from discord.ext import commands
import sqlite3
import requests
from io import BytesIO
from PIL import Image
from .utils import *
import asyncio
import config

intents = discord.Intents.all()
intents.message_content = True

# Comando para mostrar un embed con la información de los equipos
@commands.command(name='mostrar_match')
async def mostrar_match(ctx, *, match_identifier: str):
    conn = connect_db('database.db')
    cursor = conn.cursor()

    if match_identifier.isdigit():
        match_id = int(match_identifier)
        match = fetch_match_data_by_id(cursor, match_id)
        if not match:
            await ctx.send("Partido no encontrado.")
            conn.close()
            return
        
        team1_id, team2_id, team1_result, team2_result = match
        team1 = get_team_data(cursor, team1_id)
        team2 = get_team_data(cursor, team2_id)

        if not team1 or not team2:
            await ctx.send("Uno de los equipos no fue encontrado.")
            conn.close()
            return

        combined_image_bytes = fetch_and_combine_images(team1[1], team2[1])
        description = f"{team1[0]} {team1_result}-{team2_result} {team2[0]}" if team1_result is not None and team2_result is not None else f"{team1[0]} VS {team2[0]}"
        
        with BytesIO(combined_image_bytes) as image_file:
            file = discord.File(fp=image_file, filename='combined_image.png')
            embed = discord.Embed(title=f"Match {match_id}", description=description, color=0x00ff00)
            embed.set_image(url="attachment://combined_image.png")
            await ctx.send(embed=embed, file=file)
    else:
        matches = fetch_matches_by_team(cursor, match_identifier)
        if not matches:
            await ctx.send(f"No se encontraron resultados para el equipo {match_identifier}.")
            conn.close()
            return

        embed = discord.Embed(title=f"Resultados para el equipo {match_identifier}", color=0x00ff00)
        for match in matches:
            match_id, team1_name, team2_name, team1_result, team2_result = match
            description = f"{team1_name} {team1_result}-{team2_result} {team2_name}" if team1_result is not None and team2_result is not None else f"{team1_name} VS {team2_name}"
            embed.add_field(name=f"Match ID: {match_id}", value=description, inline=False)

        await ctx.send(embed=embed)

    conn.close()

@commands.command(name='predecir')
async def predecir(ctx):
    conn = connect_db('database.db')
    cursor = conn.cursor()
    bot = config.bot

    # Obtener los partidos
    cursor.execute('''
        SELECT m.id_match, t1.name, t1.image, t2.name, t2.image, m.team1_result, m.team2_result
        FROM match m
        JOIN teams t1 ON m.team1 = t1.id
        JOIN teams t2 ON m.team2 = t2.id
        WHERE m.state = 0
    ''')
    matches = cursor.fetchall()
    conn.close()

    if not matches:
        await ctx.send("No hay partidos disponibles")
        return

    embeds = []
    files = []
    botones_descripcion = (
        "**Reacciones para predecir el resultado:**\n"
        "1️⃣: 3-0\n"
        "2️⃣: 3-1\n"
        "3️⃣: 3-2\n"
        "4️⃣: 2-3\n"
        "5️⃣: 1-3\n"
        "6️⃣: 0-3\n"
    )

    for match in matches:
        match_id, team1_name, team1_image, team2_name, team2_image, team1_result, team2_result = match
        combined_image_bytes = fetch_and_combine_images(team1_image, team2_image)
        description = f"{team1_name} {team1_result}-{team2_result} {team2_name}\n\n{botones_descripcion}" if team1_result is not None and team2_result is not None else f"{team1_name} VS {team2_name}\n\n{botones_descripcion}"

        image_file = discord.File(fp=BytesIO(combined_image_bytes), filename=f'combined_image_{match_id}.png')
        files.append(image_file)

        embed = discord.Embed(title=f"Match {match_id}", description=description, color=0x00ff00)
        embed.set_image(url=f"attachment://combined_image_{match_id}.png")
        embeds.append(embed)

    current_index = 0

    async def update_message(message):
        current_embed = embeds[current_index]
        current_file = files[current_index]
        with BytesIO(current_file.fp.getvalue()) as image_file:
            image_file.seek(0)
            new_file = discord.File(fp=image_file, filename=current_file.filename)
            await message.edit(embed=current_embed, attachments=[new_file])

    message = await ctx.send(embed=embeds[current_index], file=files[current_index])

    await message.add_reaction('⬅️')
    await message.add_reaction('1️⃣')
    await message.add_reaction('2️⃣')
    await message.add_reaction('3️⃣')
    await message.add_reaction('4️⃣')
    await message.add_reaction('5️⃣')
    await message.add_reaction('6️⃣')
    await message.add_reaction('➡️')

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣'] and reaction.message.id == message.id

    async def handle_reactions():
        nonlocal current_index
        while True:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                await message.remove_reaction(reaction, user)

                if str(reaction.emoji) == '➡️':
                    current_index = (current_index + 1) % len(embeds)
                elif str(reaction.emoji) == '⬅️':
                    current_index = (current_index - 1) % len(embeds)
                elif str(reaction.emoji) in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣']:
                    results_map = {
                        '1️⃣': (3, 0),
                        '2️⃣': (3, 1),
                        '3️⃣': (3, 2),
                        '4️⃣': (2, 3),
                        '5️⃣': (1, 3),
                        '6️⃣': (0, 3)
                    }
                    team1_result, team2_result = results_map[str(reaction.emoji)]
                    current_match_id = matches[current_index][0]

                    conn = connect_db('database.db')
                    cursor = conn.cursor()
                    cursor.execute('SELECT id_user FROM user WHERE uid_discord = ?', (str(user.id),))
                    user_id = cursor.fetchone()
                    if user_id:
                        save_prediction(cursor, user_id[0], current_match_id, team1_result, team2_result)
                        conn.commit()
                    conn.close()

                await update_message(message)

            except asyncio.TimeoutError:
                await ctx.send("Tiempo de espera agotado. Por favor intenta nuevamente.")
                break

    bot.loop.create_task(handle_reactions())

@commands.command(name='points')
async def points(ctx):
    # Conectar a la base de datos
    conn = connect_db('database.db')
    cursor = conn.cursor()

    # Obtener el uid_discord del usuario que invocó el comando
    discord_id = ctx.author.id

    # Buscar el id_user correspondiente al uid_discord
    cursor.execute('SELECT id_user, puntos FROM user WHERE uid_discord = ?', (discord_id,))
    user = cursor.fetchone()

    if not user:
        await ctx.send("No estás registrado pibe.")
        conn.close()
        return

    user_id, current_points = user

    # Obtener todos los partidos con estado 1
    cursor.execute('SELECT id_match, team1_result, team2_result FROM match WHERE state = 1')
    matches = cursor.fetchall()

    # Inicializar puntos adicionales para el usuario
    additional_points = 0

    # Obtener las predicciones del usuario que no han sido procesadas
    cursor.execute('SELECT match, team1_result, team2_result FROM prediction WHERE user = ? AND flag = 0', (user_id,))
    predictions = cursor.fetchall()

    # Procesar cada predicción no procesada
    for prediction in predictions:
        match_id, predicted_team1_result, predicted_team2_result = prediction

        # Buscar el partido correspondiente en la lista de partidos
        match = next((m for m in matches if m[0] == match_id), None)

        if match:
            match_team1_result, match_team2_result = match[1], match[2]

            # Comparar resultados
            if match_team1_result == predicted_team1_result and match_team2_result == predicted_team2_result:
                # Predicción exacta, sumar 3 puntos
                additional_points += 3
            elif (match_team1_result > match_team2_result and predicted_team1_result > predicted_team2_result) or \
                 (match_team1_result < match_team2_result and predicted_team1_result < predicted_team2_result):
                # Predicción del equipo ganador correcta, pero no el resultado exacto
                additional_points += 1

            # Marcar la predicción como procesada
            cursor.execute('UPDATE prediction SET flag = 1 WHERE user = ? AND match = ?', (user_id, match_id))

    # Actualizar los puntos del usuario en la base de datos si se sumaron nuevos puntos
    if additional_points > 0:
        cursor.execute('UPDATE user SET puntos = puntos + ? WHERE id_user = ?', (additional_points, user_id))
        conn.commit()

    # Calcular puntos totales
    total_points = current_points + additional_points

    # Cerrar la conexión
    conn.close()

    # Enviar mensaje al usuario con su puntaje total
    await ctx.send(f"{ctx.author.mention}, tus puntos han sido actualizados.\nPuntos actuales: {total_points}.")

