## chess-com-bot

A Chess.com bot based on the Stockfish chess engine and the Selenium WebDriver.

- Engine's ELO rating, realistic move delays and other properties can be modified in the command line arguments.


- Supported on any platform that can run Docker/Docker-Selenium and on Windows.

### Setup (docker-selenium):

1. Install Docker
2. Build container images: `docker/docker_build.bat` / `docker/docker_build.sh`. (once / to apply changes)
3. Run the docker-compose: `docker_main.bat` / `docker_main.sh`.
4. Wait until Selenium containers are accessible at http://localhost:7900/ (interface: NoVNC)
5. Optional properties that can be modified in `docker/docker-compose.yml`:
   - `elo_rating` - engine's ELO rating (default value: `-1`)
   - `game_timer_ms` - game timer in milliseconds (default value: `150000`)
   - `first_move_w` - initial move when playing white pieces (default value: `"e2e4"`)
   - `enable_move_delay` - enable delay between moves (default value: `False`)
   - `next_game_auto` - start the next game automatically (default value: `True`)
7. To exit the program, run ```cd docker && docker-compose stop```, the containers can as well be stopped from the Docker Desktop UI.

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
   Unzip the contents into the ./stockfish/ directory of the project path.
   The executable should be renamed to "stockfish.exe"


3. Ensure that your Chrome version is supported by Selenium 4.17.0


4. Run
   ```cmd
   "./venv/Scripts/python" main.py
   ```
   
5. Optional command line arguments:
   - `--elo-rating` - engine's ELO rating (default value: `-1`)
   - `--game-timer-ms` - game timer in milliseconds (default value: `150000`)
   - `--first-move-w` - initial move when playing white pieces (default value: `"e2e4"`)
   - `--enable-move-delay` - enable delay between moves (default value: `False`)
   - `--next-game-auto` - start the next game automatically (default value: `True`)
   - `--help` - list all available options
   

6. To exit the program, simply close the Chrome tab, or the command prompt window.

### Tested OS & Chrome version:

- Windows 11 Version 23H2 (Build 22631.3007); 
- Chrome 121.0.6167.161 (Official Build) (64-bit) (cohort: Stable) 

### Disclaimer

The software is provided as-is, without warranties of any kind. The author is not responsible for any adverse effects, including but not limited to account bans, resulting from the use of this bot.

### Preview:

https://github.com/al3xkras/chess-com-bot-selenium/assets/62184786/eb664955-6a86-44bd-8daa-43dfb16954b2