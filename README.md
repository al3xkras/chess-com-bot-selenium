
# chess-com-bot

A Docker-based chess.com bot powered by **Selenium WebDriver** and the **Stockfish** chess engine.

---

## ✨ Features

- ✅ Runs either in **Docker** or locally on the host system  
- ✅ Simple configuration (see available options in `config.env`)  
- ✅ Fully or partially automated (depending on configuration)  
- ✅ Supported on **Windows 10/11** and **Linux** (tested on Ubuntu 24.04)

---

## 🚧 Currently Unimplemented

- Persistent browser profiles when `STARTUP_TYPE=docker`

---

## ⚙️ Configuration Options

Below is an overview of the supported environment variables defined in `config.env`:

### Core Settings

- **`STARTUP_TYPE`**: `local` | `docker`  
  Determines whether the bot runs locally or inside Docker.

- **`ELO_RATING`**: Integer ≥ -1  
  If `ELO_RATING <= 0`, Stockfish will not limit its ELO.

- **`FIRST_MOVE_W`**:  
  The opening move played when the bot has the white pieces.

- **`GAME_TIMER_MS`**:  
  Game timer in milliseconds. Only affects maximum move delay.  
  Ignored if `ENABLE_MOVE_DELAY=False`.

- **`GAME_TYPE`**:  
  One of:
  ```
  1min | 1+1 | 2+1 | 3min | 3+2 | 5min | 10min | 15+10 | 30min |
  random_leq5min | random_leq10min
  ```
  - `random_leq5min` / `random_leq10min` selects a random mode up to blitz/rapid.
  - `GAME_TIMER_MS` is **not adjusted automatically** when using random modes.

- **`ENABLE_MOVE_DELAY`**: `True` | `False`  
  Enables realistic move delays.  
  If `False`, the bot plays as fast as possible.

- **`AUTOSTART_FIRST_GAME`**: `True` | `False`  
  Automatically starts the first game.  
  ⚠️ Cannot log into a chess.com account if enabled.

---

### Docker-Specific Settings

- **`NUM_REPLICAS`**: Positive integer  
  Number of Docker replica containers to start.

- **`REPLICA_PORTS`**:  
  Must match `NUM_REPLICAS`:
  - Single replica → single port (e.g., `7910`)
  - Multiple replicas → port range (e.g., `7911-7914` for 4 replicas)

- **`CHROMIUM_SCREEN_WIDTH` / `CHROMIUM_SCREEN_HEIGHT`**:  
  Chromium window dimensions (only relevant when `STARTUP_TYPE=docker`).

- **`SELENIUM_NODE_IDLE_TIMEOUT_SECONDS`**:  
  Idle timeout in seconds.  
  The Chrome session restarts after inactivity or a crash.

- **`OPEN_BROWSER`**: `True` | `False`  
  Automatically opens VNC URLs in the host's default browser.  
  Opens multiple tabs if `NUM_REPLICAS > 1`.

---

# 🐳 Docker Setup

1. Install **Docker** and **Docker Compose**
2. Set `STARTUP_TYPE=docker` in `config.env`
3. Run the main script:
   ```bash
   ./main.sh
   ```
   or on Windows:
   ```powershell
   ./main.ps1
   ```
   > On Linux, root authentication may be required to access the Docker daemon.

4. If `OPEN_BROWSER=True`, the browser opens automatically once Selenium nodes are initialized.
5. If `AUTOSTART_FIRST_GAME=True`, the first game starts automatically. Otherwise, start it manually.
6. To stop the bot:
   ```bash
   ./main.<sh/ps1> stop
   ```
   or
   ```bash
   ./main.<sh/ps1> kill
   ```

---

# 💻 Local Setup (Windows / Linux)

> ⚠️ The local setup may result in unexpected issues depending on your host system.  
> Docker is recommended for maximum stability.

0. Install Python >=3.10. Add Python to system PATH.
1. Set `STARTUP_TYPE=local` in `config.env`.
2. Make sure the `STOCKFISH_URL` matches your OS and architecture.
3. Run:
   ```bash
   ./main.sh
   ```
   or:
   ```powershell
   ./main.ps1
   ```
   - Note that the first startup may take more time, because Selenium will have to pull the Chromium driver if it is not installed.
4. To stop the bot:
   - Terminate the process in the terminal, or  
   - Close the browser window.

---

# ⚠️ Disclaimer

This software is provided **as is**, without warranty of any kind.  
The author is not responsible for any adverse effects resulting from its use, including but not limited to **account bans**.
