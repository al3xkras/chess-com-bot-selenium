## chess-com-bot

Fast, single-file Chess.com bot based on the Selenium automation suite and the Stockfish chess engine.
The bot can optionally imitate realistic move delays, based on the Stockfish evaluation time. 
This behavior can be enabled via the Command-Line Interface (CLI) or docker-compose. 
Chess-com-bot is currently supported on Windows and Docker-Selenium environments.

### Setup (docker-selenium):

1. Install Docker.
2. Run `docker/docker_build.bat` / `docker/docker_build.sh`.
3. Run `docker_main.bat` / `docker_main.sh`.
4. Wait for the containers to load (avg. 5s; excluding docker pull & docker build)
5. To access the NoVNC interface, open http://localhost:7900/.
6. Command line arguments can be modified in `docker/docker-compose.yml`. Requires rebuilding the main Docker container (`docker/build.bat`).
   - `--elo-rating` - engine's ELO rating (default value: `-1`)
   - `--game-timer-ms` - game timer in milliseconds (default value: `150000`)
   - `--first-move-w` - initial move when playing white pieces (default value: `"e2e4"`)
   - `--enable-move-delay` - enable delay between moves (default value: `False`)
   - `--help` - list all available options

   
### Setup on Windows

1. Create a virtual environment:
   > git clone https://github.com/al3xkras/chess-com-bot-selenium chess-com-bot
      
   > cd ./chess-com-bot

   > pip install virtualenv
   
   > virtualenv venv  
   

2. Install required packages:
    >"./venv/Scripts/pip" install -r "requirements.txt"

3. Choose a compatible Stockfish release at
   (https://github.com/official-stockfish/Stockfish/releases).
   Unzip the contents into the ./stockfish/ directory of the project path.
   The Stockfish executable's file extension should be removed.


4. Check if the installed version of Chrome is compatible with Selenium 4.17.0


5. Run
   ```code
   "./venv/Scripts/python" main.py
   ```


### Tested OS & Chrome version:

- Windows 11 Version 23H2 (Build 22631.3007); 
- Chrome 121.0.6167.161 (Official Build) (64-bit) (cohort: Stable) 

### Disclaimer

The software is provided as-is, without warranties of any kind. The author is not responsible for any adverse effects, including but not limited to account bans, resulting from the use of this bot. Use it responsibly and at your own discretion.


### Preview:

https://github.com/al3xkras/chess-com-bot-selenium/assets/62184786/eb664955-6a86-44bd-8daa-43dfb16954b2