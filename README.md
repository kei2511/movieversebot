# MovieVerse Bot

A Telegram bot for searching movies, actors, trending films, and finding nearby cinemas using TMDb API.

## Features

- 🔍 Search movies by title
- 🎭 Search actors/actresses
- 🎬 Get trending movies
- 🏷️ Browse movies by genre
- ⭐ Save favorite movies
- 🎫 Find nearby cinemas
- 📱 Interactive menu system

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` file from `.env.example` and add your tokens:
   ```
   BOT_TOKEN=your_telegram_bot_token
   TMDB_API_KEY=your_tmdb_api_key
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Environment Variables

- `BOT_TOKEN`: Your Telegram bot token from @BotFather
- `TMDB_API_KEY`: Your TMDb API key from https://www.themoviedb.org/settings/api

## Commands

- `/start` - Start the bot and show main menu
- `/help` - Show help information
- `/search` - Search for movies
- `/genre` - Browse movies by genre
- `/actor` - Search for actors
- `/trending` - Get trending movies
- `/favorite` - Add movie to favorites
- `/favorites` - View your favorite movies
- `/nearest_cinema` - Find nearby cinemas

## Deployment

This bot can be deployed to various free platforms:
- Railway
- Render
- Heroku
- Fly.io

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
