## chess-com-bot

A Chess.com bot based on the Selenium WebDriver for browser automation and the Stockfish chess engine for position evaluation.

Features:

- Fully configurable (using command line arguments or docker-compose, see the list of available configurations below).
- Fast response speed (minimum latency of about 100-150ms added to the Stockfish thinking time). Custom delays configurable.
- Low resource usage (Docker-based build).
- Cross-platform (supported on Linux, Docker and Windows). Most linux distributions (debian/ubuntu) should be supported but may require additional setup. Check out the Dockerfile (ubuntu-based) for more insight. Also make sure there exists a Stockfish build for your distribution, at the [Stockfish repo](https://github.com/official-stockfish/Stockfish/releases/)
- The bot can work autonomously after the first game is started manually.
- The bot closes most of the pop-up windows automatically.
- The bot handles network/chess.com-related bugs and should continue to work if any occur.

### Setup (Docker):

1. Install Docker and Docker compose. 
2. Run containers using the Docker compose: `docker_main.bat` / `docker_main.sh`.

   List of configurable docker-compose properties `docker/docker-compose.yml`:
   - `elo_rating` - engine's ELO rating (default value: `-1`)
   - `game_timer_ms` - game timer in milliseconds (default value: `150000`)
   - `first_move_w` - initial move when playing white pieces (default value: `"e2e4"`)
   - `enable_move_delay` - enable delay between moves (default value: `False`)
   - `next_game_auto` - start the next game automatically (default value: `True`)
4. Wait until a Chrome NoVNC session is loaded at http://localhost:7901/
5. To check if the bot is working properly, start the first game manually and wait until the first move is made.
6. To exit the program, run ```cd docker && docker compose stop```, or stop the containers from the Docker Desktop UI.

### Setup on Windows

1. Create a virtual environment:
   ```cmd
   git clone --depth 1 https://github.com/al3xkras/chess-com-bot-selenium chess-com-bot 
   cd ./chess-com-bot
   ```
   
   ```cmd
   pip install virtualenv && virtualenv venv
   ```
   
   ```cmd
   "venv/Scripts/pip" install -r "requirements.txt"
   ```

2. Choose a compatible Stockfish release at the 
   [Stockfish repo](https://github.com/official-stockfish/Stockfish/releases).
   
   Example: https://github.com/official-stockfish/Stockfish/releases/tag/sf_16.1 .


3. Unzip the stockfish executable into the ./stockfish/ directory. Rename the executable to "stockfish.exe" or "stockfish"


4. Run the bot using the command line:
   ```cmd
   "./venv/Scripts/python" main.py
   ```

   List of configurable command line arguments:
   - `--elo-rating` - engine's ELO rating (default value: `-1`)
   - `--game-timer-ms` - game timer in milliseconds (default value: `150000`)
   - `--first-move-w` - initial move when playing white pieces (default value: `"e2e4"`)
   - `--enable-move-delay` - enable delay between moves (default value: `False`)
   - `--next-game-auto` - start the next game automatically (default value: `True`)
   - `--help` - list all available options
   

### Tested Windows OS & Chrome:

- Windows 11 Version 23H2 (Build 22631.3007); 
- Chrome 121.0.6167.161 (Official Build) (64-bit) (cohort: Stable)

### Disclaimer

The software is provided as-is, without warranties of any kind. The author is not responsible for any adverse effects, including but not limited to account bans, resulting from the use of this bot.

### Preview:

https://github.com/al3xkras/chess-com-bot-selenium/assets/62184786/eb664955-6a86-44bd-8daa-43dfb16954b2
