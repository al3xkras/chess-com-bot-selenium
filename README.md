## chess-com-bot

A Chess.com bot based on the Stockfish chess engine and Selenium WebDriver.

- Fully configurable (using the command line arguments or the docker-compose, see the list of available configurations below).
- Supported platforms: Docker (Docker-Selenium) and Windows

### Setup (Docker):

1. Install Docker
2. Build container images: `docker/docker_build.bat` / `docker/docker_build.sh`. (once / to apply changes)
3. Run containers using the docker-compose: `docker_main.bat` / `docker_main.sh`.

   List of configurable docker-compose properties `docker/docker-compose.yml`:
   - `elo_rating` - engine's ELO rating (default value: `-1`)
   - `game_timer_ms` - game timer in milliseconds (default value: `150000`)
   - `first_move_w` - initial move when playing white pieces (default value: `"e2e4"`)
   - `enable_move_delay` - enable delay between moves (default value: `False`)
   - `next_game_auto` - start the next game automatically (default value: `True`)
4. Wait until the Selenium Chrome node is accessible at http://localhost:7900/ (interface: NoVNC)
5. To exit the program, run ```cd docker && docker-compose stop```, or stop the containers from the Docker Desktop UI.

### Setup on Windows

1. Create a virtual environment:
   ```cmd
   git clone --depth 1 https://github.com/al3xkras/chess-com-bot-selenium chess-com-bot 
   cd ./chess-com-bot
   ```
   
   ```cmd
   pip install virtualenv & virtualenv venv
   ```
   
   ```cmd
   "venv/Scripts/pip" install -r "requirements.txt"
   ```

2. Choose a compatible Stockfish release at
   (https://github.com/official-stockfish/Stockfish/releases).
   
   Example: https://github.com/official-stockfish/Stockfish/releases/tag/sf_16.1 .


3. Unzip the stockfish executable into the ./stockfish/ directory.


4. Rename the executable to "stockfish.exe" or "stockfish"


5. Run the bot using the command line:
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
   

### Tested OS & Chrome:

- Windows 11 Version 23H2 (Build 22631.3007); 
- Chrome 121.0.6167.161 (Official Build) (64-bit) (cohort: Stable) 

### Disclaimer

The software is provided as-is, without warranties of any kind. The author is not responsible for any adverse effects, including but not limited to account bans, resulting from the use of this bot.

### Preview:

https://github.com/al3xkras/chess-com-bot-selenium/assets/62184786/eb664955-6a86-44bd-8daa-43dfb16954b2