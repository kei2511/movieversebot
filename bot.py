import asyncio
import json
import nest_asyncio
import os
import requests
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Install required packages
# !pip install python-telegram-bot==20.4 nest_asyncio
# Aktifkan nest_asyncio untuk mengatasi masalah event loop
nest_asyncio.apply()

# Get environment variables (Railway sets them automatically)
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Debug logging for Railway
logger.info(f"BOT_TOKEN exists: {bool(BOT_TOKEN)}")
logger.info(f"TMDB_API_KEY exists: {bool(TMDB_API_KEY)}")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required - check Railway Variables")
if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY environment variable is required - check Railway Variables")
FAVORITES_FILE = "favorites.json"

# Create empty favorites file if it doesn't exist
if not os.path.exists(FAVORITES_FILE):
    with open(FAVORITES_FILE, 'w') as f:
        f.write('{}')

# Load genres from TMDb
def load_genres():
    data = tmdb_request("genre/movie/list")
    return {genre['name'].lower(): genre['id'] for genre in data.get("genres", [])}

# API Functions
def tmdb_request(endpoint, params=None):
    base_params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    if params:
        base_params.update(params)
    try:
        response = requests.get(f"https://api.themoviedb.org/3/{endpoint}", params=base_params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error in TMDb request: {e}")
        return {}

# Favorite Functions
def load_favorites():
    try:
        with open(FAVORITES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_favorites(favorites):
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favorites, f)

# Helper Functions
def create_movie_keyboard(movies, callback_prefix="detail"):
    keyboard = []
    for movie in movies[:5]:  # Limit to 5 results
        movie_id = movie["id"]
        movie_title = movie["title"]
        release_year = movie.get("release_date", "Unknown")[:4] if movie.get("release_date") else "Unknown"
        display_name = f"{movie_title} ({release_year})"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"{callback_prefix}_{movie_id}")])
    keyboard.append([InlineKeyboardButton("🎛️ Menu", callback_data="menu_menu")])
    return InlineKeyboardMarkup(keyboard)

def create_main_menu():
    start_message = f"""
    🎥 Selamat datang di Movie Search Bot! 🍿
    Siap menjelajahi dunia film? Dari blockbuster terbaru hingga klasik favorit, kami punya semua yang kamu cari!
    Gunakan tombol di bawah untuk mulai petualanganmu:
    - Cari film, aktor, atau genre favoritmu
    - Temukan film trending atau bioskop terdekat
    - Simpan film kesukaanmu di daftar favorit
    Klik **🎛️ Menu** untuk melihat semua fitur!
    """
    keyboard = [
        [InlineKeyboardButton("🔍 Cari Film", callback_data="menu_search"),
         InlineKeyboardButton("🎭 Cari Aktor", callback_data="menu_actor")],
        [InlineKeyboardButton("🎬 Film Trending", callback_data="menu_trending"),
         InlineKeyboardButton("🏷️ Genre Film", callback_data="menu_genres")],
        [InlineKeyboardButton("⭐ Tambah Favorit", callback_data="menu_favorite"),
         InlineKeyboardButton("📜 List Favorit", callback_data="menu_favorites")],
        [InlineKeyboardButton("🎫 Cari Bioskop", callback_data="menu_cinema"),
         InlineKeyboardButton("🎛️ Menu", callback_data="menu_menu")],
        [InlineKeyboardButton("❓ Bantuan", callback_data="menu_help")]
    ]
    return start_message, InlineKeyboardMarkup(keyboard)

def create_error_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🎛️ Menu", callback_data="menu_menu")]])

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_message, reply_markup = create_main_menu()
    await update.message.reply_text(start_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if hasattr(update, 'callback_query') else None
    try:
        logger.info("Processing help_command")
        help_message = f"""
        🎬 Panduan Menu Movie Search Bot 🍿
        Berikut adalah penjelasan tombol menu kami:
        - 🔍 **Cari Film**: Cari film berdasarkan judul.
        - 🎭 **Cari Aktor**: Temukan film berdasarkan nama aktor/aktris.
        - 🎬 **Film Trending**: Lihat film yang sedang populer saat ini.
        - 🏷️ **Genre Film**: Jelajahi film berdasarkan genre (action, comedy, dll.).
        - ⭐ **Tambah Favorit**: Tambahkan film ke daftar favoritmu.
        - 📜 **List Favorit**: Lihat daftar film favoritmu.
        - 🎫 **Cari Bioskop**: Temukan bioskop terdekat dengan lokasimu.
        - 🎛️ **Menu**: Kembali ke menu utama.
        - ❓ **Bantuan**: Tampilkan panduan ini.
        Klik **🎛️ Menu** untuk kembali menjelajah!
        """
        keyboard = [
            [InlineKeyboardButton("🎛️ Menu", callback_data="menu_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.message.reply_text(help_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(help_message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        if query:
            await query.message.reply_text("❌ Terjadi kesalahan saat menampilkan bantuan. Silakan coba lagi.", reply_markup=create_error_keyboard())
        else:
            await update.message.reply_text("❌ Terjadi kesalahan saat menampilkan bantuan. Silakan coba lagi.", reply_markup=create_error_keyboard())

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ Please enter a movie title after /search.", reply_markup=create_error_keyboard())
        return
    movies = search_movie_by_title(query)
    if not movies:
        await update.message.reply_text(f"❌ No movies found for '{query}'.", reply_markup=create_error_keyboard())
        return
    reply_markup = create_movie_keyboard(movies)
    await update.message.reply_text("🎬 Movies found:", reply_markup=reply_markup)

def search_movie_by_title(title):
    data = tmdb_request("search/movie", {"query": title})
    return data.get("results", [])

async def show_movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data.split("_")[1]
    movie = get_movie_details(movie_id)
    if not movie:
        await query.edit_message_text("❌ Movie details not found.", reply_markup=create_error_keyboard())
        return
    title = movie.get("title", "N/A")
    overview = movie.get("overview") or "Synopsis not available."
    rating = movie.get("vote_average", 0)
    release_date = movie.get("release_date", "N/A")
    trailer_url = get_movie_trailer(movie_id)
    trailer_info = f"\n🎬 Trailer: {trailer_url}" if trailer_url else "\n🎬 Trailer: Not available."
    cast = get_movie_cast(movie_id)
    cast_list = ", ".join([actor["name"] for actor in cast]) if cast else "Cast information not available."
    message = f"""
    🎬 {title}
    📅 Release Date: {release_date}
    ⭐ Rating: {rating}
    📝 Synopsis:
    {overview}
    👥 Cast:
    {cast_list}{trailer_info}
    """
    await query.edit_message_text(message, reply_markup=create_error_keyboard())

def get_movie_details(movie_id):
    return tmdb_request(f"movie/{movie_id}")

def get_movie_trailer(movie_id):
    data = tmdb_request(f"movie/{movie_id}/videos")
    videos = data.get("results", [])
    for video in videos:
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            return f"https://www.youtube.com/watch?v={video['key']}"
    return None

def get_movie_cast(movie_id):
    data = tmdb_request(f"movie/{movie_id}/credits")
    return data.get("cast", [])[:5]

async def search_actor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ Masukkan nama aktor/aktris setelah /actor.", reply_markup=create_error_keyboard())
        return
    data = tmdb_request("search/person", {"query": query})
    actors = data.get("results", [])
    if not actors:
        await update.message.reply_text(f"❌ Tidak ada aktor/aktris ditemukan untuk '{query}'.", reply_markup=create_error_keyboard())
        return
    actor = actors[0]
    name = actor["name"]
    known_for = actor["known_for"]
    reply_markup = create_movie_keyboard(known_for)
    profile_path = actor.get("profile_path")
    profile_url = f"https://image.tmdb.org/t/p/w500{profile_path}" if profile_path else "Foto tidak tersedia."
    message = f"""
    🎭 {name}
    🖼️ Foto:
    {profile_url}
    """
    await update.message.reply_text(message)
    await update.message.reply_text("🎬 Movies starring this actor/actress:", reply_markup=reply_markup)

async def recommend_movie_by_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    genre_name = " ".join(context.args).lower()
    if not genre_name:
        await update.message.reply_text("⚠️ Please enter a genre name after /genre.", reply_markup=create_error_keyboard())
        return
    genre_id = GENRES.get(genre_name)
    if not genre_id:
        await update.message.reply_text(f"❌ Genre '{genre_name}' not found.", reply_markup=create_error_keyboard())
        return
    movies = get_movies_by_genre(genre_id)
    if not movies:
        await update.message.reply_text(f"❌ No movie recommendations available for genre '{genre_name}'.", reply_markup=create_error_keyboard())
        return
    reply_markup = create_movie_keyboard(movies)
    await update.message.reply_text(f"🎬 Movie recommendations for genre '{genre_name.capitalize()}':", reply_markup=reply_markup)

def get_movies_by_genre(genre_id):
    data = tmdb_request("discover/movie", {"with_genres": genre_id, "page": 1})
    return data.get("results", [])

async def trending_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = tmdb_request("trending/movie/day")
    movies = data.get("results", [])
    if not movies:
        await update.message.reply_text("❌ Tidak ada film tren saat ini.", reply_markup=create_error_keyboard())
        return
    reply_markup = create_movie_keyboard(movies)
    await update.message.reply_text("🎬 Film yang sedang tren:", reply_markup=reply_markup)

async def add_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ Please enter a movie title after /favorite.", reply_markup=create_error_keyboard())
        return
    movies = search_movie_by_title(query)
    if not movies:
        await update.message.reply_text(f"❌ No movies found for '{query}'.", reply_markup=create_error_keyboard())
        return
    reply_markup = create_movie_keyboard(movies, callback_prefix="save")
    await update.message.reply_text("🎬 Select the movie you want to save:", reply_markup=reply_markup)

async def save_favorite_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data.split("_")[1]
    movie = get_movie_details(movie_id)
    if not movie:
        await query.edit_message_text("❌ No movie details found.", reply_markup=create_error_keyboard())
        return
    movie_title = movie.get("title", "Unknown")
    favorites = load_favorites()
    user_id = str(update.callback_query.from_user.id)
    if user_id not in favorites:
        favorites[user_id] = []
    if movie_title.lower() in [fav.lower() for fav in favorites[user_id]]:
        await query.edit_message_text(f"❌ '{movie_title}' sudah ada di daftar favorit Anda.", reply_markup=create_error_keyboard())
        return
    favorites[user_id].append(movie_title)
    save_favorites(favorites)
    await query.edit_message_text(f"✅ '{movie_title}' telah ditambahkan ke daftar favorit Anda.", reply_markup=create_error_keyboard())

async def view_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favorites = load_favorites()
    user_id = str(update.message.from_user.id)
    if user_id not in favorites or not favorites[user_id]:
        await update.message.reply_text("❌ Anda belum memiliki film favorit.", reply_markup=create_error_keyboard())
        return
    message = "⭐ Daftar film favorit Anda:\n"
    for movie in favorites[user_id]:
        message += f"- {movie}\n"
    await update.message.reply_text(message, reply_markup=create_error_keyboard())

async def minta_lokasi_bioskop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("📍 Kirim Lokasi", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Silakan kirim lokasi kamu untuk mencari bioskop terdekat:",
        reply_markup=reply_markup
    )

async def bioskop_terdekat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    if not location:
        await update.message.reply_text("📍 Silakan kirim lokasi kamu terlebih dahulu.", reply_markup=create_error_keyboard())
        return
    lat = location.latitude
    lon = location.longitude
    link_maps = f"https://www.google.com/maps/search/bioskop/@{lat},{lon},15z"
    await update.message.reply_text(f"🎬 Berikut link bioskop terdekat:\n{link_maps}", reply_markup=ReplyKeyboardRemove())

# Handle Menu Buttons
async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split("_")[1]
    logger.info(f"Handling menu button with action: {action}")
    
    try:
        if action == "search":
            context.user_data['state'] = 'search'
            await query.message.reply_text("🔍 Ketik judul film yang ingin dicari:")
        elif action == "actor":
            context.user_data['state'] = 'actor'
            await query.message.reply_text("🎭 Ketik nama aktor/aktris:")
        elif action == "favorite":
            context.user_data['state'] = 'favorite'
            await query.message.reply_text("⭐ Ketik judul film yang ingin ditambahkan ke favorit:")
        elif action == "trending":
            data = tmdb_request("trending/movie/day")
            movies = data.get("results", [])
            if not movies:
                await query.message.reply_text("❌ Tidak ada film tren saat ini.", reply_markup=create_error_keyboard())
                return
            reply_markup = create_movie_keyboard(movies)
            await query.message.reply_text("🎬 Film yang sedang tren:", reply_markup=reply_markup)
        elif action == "genres":
            genres_list = list(GENRES.keys())[:10]
            keyboard = []
            for i in range(0, len(genres_list), 2):
                row = [InlineKeyboardButton(genres_list[i].capitalize(), callback_data=f"genre_{genres_list[i]}")]
                if i+1 < len(genres_list):
                    row.append(InlineKeyboardButton(genres_list[i+1].capitalize(), callback_data=f"genre_{genres_list[i+1]}"))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_main")])
            await query.message.reply_text("🏷️ Pilih genre:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif action == "favorites":
            user_id = str(query.from_user.id)
            favorites = load_favorites()
            if user_id not in favorites or not favorites[user_id]:
                await query.message.reply_text("❌ Anda belum memiliki film favorit.", reply_markup=create_error_keyboard())
            else:
                daftar_favorit = "\n".join([f"- {movie}" for movie in favorites[user_id]])
                await query.message.reply_text(f"⭐ Daftar favorit Anda:\n{daftar_favorit}", reply_markup=create_error_keyboard())
        elif action == "cinema":
            keyboard = [[KeyboardButton("📍 Kirim Lokasi", request_location=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await query.message.reply_text("Silakan kirim lokasi Anda:", reply_markup=reply_markup)
        elif action == "menu":
            start_message, reply_markup = create_main_menu()
            await query.message.reply_text(start_message, reply_markup=reply_markup)
        elif action == "main":
            start_message, reply_markup = create_main_menu()
            await query.message.reply_text("🎬 Pilih menu:", reply_markup=reply_markup)
        elif action == "help":
            await help_command(update, context)
        else:
            logger.warning(f"Unknown action: {action}")
            await query.message.reply_text("❌ Perintah tidak dikenali.", reply_markup=create_error_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_menu_button: {e}")
        await query.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi.", reply_markup=create_error_keyboard())

# Handle Genre Buttons
async def handle_genre_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    genre_name = query.data.split("_")[1]
    genre_id = GENRES.get(genre_name)
    if not genre_id:
        await query.message.reply_text(f"❌ Genre '{genre_name}' not found.", reply_markup=create_error_keyboard())
        return
    movies = get_movies_by_genre(genre_id)
    if not movies:
        await query.message.reply_text(f"❌ No movie recommendations available for genre '{genre_name}'.", reply_markup=create_error_keyboard())
        return
    reply_markup = create_movie_keyboard(movies)
    await query.message.reply_text(f"🎬 Movie recommendations for genre '{genre_name.capitalize()}':", reply_markup=reply_markup)

# Text Message Handler (with State Support)
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    # Cek apakah ada state aktif
    if 'state' in context.user_data:
        state = context.user_data.pop('state')
        
        if state == 'search':
            query = text.strip()
            if query:
                context.args = query.split()
                await search_movie(update, context)
            else:
                await update.message.reply_text("❌ Judul film tidak boleh kosong.", reply_markup=create_error_keyboard())
        
        elif state == 'actor':
            query = text.strip()
            if query:
                context.args = query.split()
                await search_actor(update, context)
            else:
                await update.message.reply_text("❌ Nama aktor tidak boleh kosong.", reply_markup=create_error_keyboard())
        
        elif state == 'favorite':
            query = text.strip()
            if query:
                context.args = query.split()
                await add_favorite(update, context)
            else:
                await update.message.reply_text("❌ Judul film tidak boleh kosong.", reply_markup=create_error_keyboard())
    
    else:
        if "cari film" in text or "search movie" in text:
            query = text.replace("cari film", "").replace("search movie", "").strip()
            if query:
                context.args = query.split()
                await search_movie(update, context)
            else:
                await update.message.reply_text("🔍 Silakan masukkan judul film yang ingin dicari.\nContoh: cari film Avengers", reply_markup=create_error_keyboard())
        elif "cari aktor" in text or "search actor" in text:
            query = text.replace("cari aktor", "").replace("search actor", "").strip()
            if query:
                context.args = query.split()
                await search_actor(update, context)
            else:
                await update.message.reply_text("🎭 Ketik nama aktor atau aktris.\nContoh: cari aktor Tom Cruise", reply_markup=create_error_keyboard())
        elif "trending" in text or "film populer" in text:
            await trending_movies(update, context)
        elif "genre" in text:
            genre_name = text.replace("genre", "").strip()
            if genre_name:
                context.args = genre_name.split()
                await recommend_movie_by_genre(update, context)
            else:
                genres_list = list(GENRES.keys())[:10]
                genres_text = ", ".join([g.capitalize() for g in genres_list])
                await update.message.reply_text(f"🏷️ Silakan tentukan genre film:\nContoh: genre action\nGenre yang tersedia: {genres_text}", reply_markup=create_error_keyboard())
        elif "favorit" in text or "favorites" in text:
            if "tambah" in text or "add" in text:
                query = text.replace("tambah favorit", "").replace("add to favorites", "").strip()
                if query:
                    context.args = query.split()
                    await add_favorite(update, context)
                else:
                    await update.message.reply_text("⭐ Ketik judul film untuk favorit.\nContoh: tambah favorit Inception", reply_markup=create_error_keyboard())
            else:
                await view_favorites(update, context)
        elif "bioskop" in text or "cinema" in text:
            await minta_lokasi_bioskop(update, context)
        elif "bantuan" in text or "help" in text:
            await help_command(update, context)
        elif "menu" in text or "start" in text:
            await start(update, context)
        else:
            start_message, reply_markup = create_main_menu()
            await update.message.reply_text("Saya tidak mengerti permintaan Anda. Silakan pilih dari menu di bawah:", reply_markup=reply_markup)

# Main Function
async def main_async():
    global GENRES
    GENRES = load_genres()
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_movie))
    application.add_handler(CommandHandler("genre", recommend_movie_by_genre))
    application.add_handler(CommandHandler("actor", search_actor))
    application.add_handler(CommandHandler("trending", trending_movies))
    application.add_handler(CommandHandler("favorite", add_favorite))
    application.add_handler(CommandHandler("favorites", view_favorites))
    application.add_handler(CommandHandler("nearest_cinema", minta_lokasi_bioskop))

    # Callback handlers
    application.add_handler(CallbackQueryHandler(show_movie_details, pattern=r"^detail_\d+"))
    application.add_handler(CallbackQueryHandler(save_favorite_movie, pattern=r"^save_\d+"))
    application.add_handler(CallbackQueryHandler(handle_menu_button, pattern=r"^menu_"))
    application.add_handler(CallbackQueryHandler(handle_genre_button, pattern=r"^genre_"))

    # Location and text message handlers
    application.add_handler(MessageHandler(filters.LOCATION, bioskop_terdekat))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Bot started successfully!")

    while True:
        await asyncio.sleep(1)

# Run the bot
def run_bot():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Bot stopped by user")

if __name__ == "__main__":
    run_bot()