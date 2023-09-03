Local setup:

1. Copy the Stockfish binaries to the "$project_path"/stockfish/ directory
2. Install required packages:
    > pip install -r "requirements.txt"

3. Run
   ```code
   "./venv/Scripts/python" main.py
   ```
   Optional arguments:
   - ``` --elo-rating=-1``` - engine's ELO rating (default value: ```-1```)
   - ```--game-timer-ms=300000``` - game timer in milliseconds (default value: ```300000```)
   - ```--first-move-w="e2e4"``` - first move to play if playing white pieces (default value: ```"e2e4"```)
   - ```--enable-move-delay``` - enable delay between moves (default value: True)
   - ```--help``` - list all available options

https://github.com/al3xkras/chess-com-bot-selenium/assets/62184786/eb664955-6a86-44bd-8daa-43dfb16954b2