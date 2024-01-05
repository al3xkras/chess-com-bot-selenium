## chess-com-bot

A simple Chess.com bot based on the Selenium automation suite and the Stockfish chess engine.
By default, the bot imitates "realistic" delay between moves based on the Stockfish evaluation time.
Supports both "Play online" and "Play against a computer" Chess.com options.

Local setup (Windows)

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


4. Check if the installed version of Chrome is compatible with Selenium 4.11.2.


5. Run
   ```code
   "./venv/Scripts/python" main.py
   ```

   Optional arguments:
   - ``` --elo-rating``` - engine's ELO rating (default value: ```-1```)
   - ```--game-timer-ms``` - game timer in milliseconds (default value: ```300000```)
   - ```--first-move-w``` - first move to play if playing white pieces (default value: ```"e2e4"```)
   - ```--enable-move-delay``` - enable delay between moves (default value: ```False```)
   - ```--help``` - list all available options

Preview:

https://github.com/al3xkras/chess-com-bot-selenium/assets/62184786/eb664955-6a86-44bd-8daa-43dfb16954b2