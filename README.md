Local setup:

1. Cloning the repository and creating a virtual environment:
   > git clone https://github.com/al3xkras/chess-com-bot-selenium chess-com-bot
      
   > cd ./chess-com-bot

   > pip install virtualenv
   
   > virtualenv venv  
   
   if the "virtualenv" binary is not found after installation, make sure the site-packages pip folder is added to PATH


2. Installation of the required packages:
    >"./venv/Scripts/pip" install -r "requirements.txt"

3. Copy the Stockfish executable to the ./stockfish/ directory of the project path


4. Run
   ```code
   "./venv/Scripts/python" main.py
   ```
   Optional arguments:
   - ``` --elo-rating=-1``` - engine's ELO rating (default value: ```-1```)
   - ```--game-timer-ms=300000``` - game timer in milliseconds (default value: ```300000```)
   - ```--first-move-w="e2e4"``` - first move to play if playing white pieces (default value: ```"e2e4"```)
   - ```--enable-move-delay``` - enable delay between moves (default value: False)
   - ```--help``` - list all available options

https://github.com/al3xkras/chess-com-bot-selenium/assets/62184786/eb664955-6a86-44bd-8daa-43dfb16954b2