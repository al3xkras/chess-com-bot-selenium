import asyncio
import collections
import concurrent.futures
import itertools
import os
import pdb
import random
import sys
import threading
import traceback
import typing
from time import time, sleep

import logging
import selenium.common.exceptions
import selenium.webdriver.common.devtools.v119 as devtools
import typer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver
import selenium.webdriver.support.expected_conditions as EC

import stockfish
import chess
import json

selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.INFO)

logging.getLogger('selenium').setLevel(logging.DEBUG)
logging.getLogger('selenium.webdriver.remote').setLevel(logging.DEBUG)
logging.getLogger('selenium.webdriver.common').setLevel(logging.DEBUG)

url = "https://www.chess.com/"
stockfish_dir = "./stockfish"
stockfish_path = stockfish_dir + "/stockfish"
executor = concurrent.futures.ThreadPoolExecutor(5)

# Decrease/increase this parameter if the default move delay is too fast / too slow
MOVE_DELAY_MULTIPLIER = 1.0

PREVIOUS_FEN_POSITIONS = collections.defaultdict(lambda: 0)
NEW_GAME_BUTTON_CLICK_TIME = time()

# the browser will be refreshed after 45 seconds of matchmaking if no match was found.
NEW_GAME_BUTTON_CLICK_TIMEOUT = 45

class C:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    board = "board"
    flipped = "flipped"
    outerHTML = "outerHTML"
    square = "square-"
    piece = "piece"
    hover = "hover-"
    highlight = "highlight"
    class_ = "class"
    space = " "
    controls_xpath = "//div[@class='game-controls-controller-component' or @class='live-game-buttons-component' or @class='game-icons-container-component']"
    new_game_buttons_xpath = "//div[button[span[contains(text(),'New') or contains(text(),'Decline') or contains(text(),'Rem')]]]"
    new_game_button_sub_xpath = "./button[span[contains(text(), \"%s\")]]"
    some_id = "p1234"
    promotion_moves = ["1", "8"]
    scr_xpath = """
    _iter = document.evaluate('%s', document, null, 
        XPathResult.UNORDERED_NODE_ITERATOR_TYPE, null);
    _lst = [];
    while(1) {
        e = _iter.iterateNext();
        if (!e) break;
        _lst.push(e.getAttribute("class"));
    }
    return _lst
    """.strip()
    xpath_highlight = f'//*[contains(@class,"{highlight}")]'
    xpath_piece = '//div[contains(@class,"piece") and (contains(@class, "%d") or contains(@class, "%d"))]'
    js_add_ptr = """
    var board = document.getElementsByClassName('%s').item(0);
    var piece = document.createElement('div');

    piece.setAttribute('class', '%s');
    board.appendChild(piece);
    """
    js_rm_ptr = """
    const board = document.getElementsByClassName('%s').item(0);
    const to_rm = document.getElementsByClassName('%s');
    for (var i = 0; i < to_rm.length; i++) {
       board.removeChild(to_rm.item(i));
    }
    """
    white_pawn = "wp"
    black_queen = "bq"
    white_queen = "wq"
    promotion_window = "promotion-window"
    promotion_move_queen = "q"
    wait_1s = 1
    wait_2s = 2
    wait_5s = 5
    wait_240s = 240
    wait_50ms = 0.05
    exit_delay = 10
    task_wait = "task_wait"
    num_to_let = dict(zip(range(1, 9), "abcdefgh"))
    let_to_num = dict((v, k) for k, v in num_to_let.items())


class LogFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    green = "\x1b[32m"
    blue = "\x1b[34m"
    cyan = "\x1b[36m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = " %(asctime)s [%(name)s]: %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG:
            reset + "%(asctime)s " +
            yellow + "[%(levelname)s]" +
            cyan + " [%(name)s," +
            cyan + " %(filename)s:%(lineno)d]:" + reset +
            grey + " %(message)s" + reset,
        logging.INFO:
            reset + "%(asctime)s " +
            green + "[%(levelname)s] [" +
            green + "%(name)s," +
            green + " %(filename)s:%(lineno)d]" + reset +
            grey + ": %(message)s" + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=LogFormatter.DATE_FORMAT)
        return formatter.format(record)


stream = logging.StreamHandler(stream=sys.stdout)
stream.setFormatter(LogFormatter())
Log = logging.getLogger('chess-log')
Log.setLevel(logging.DEBUG)
Log.addHandler(stream)

if not os.path.exists(stockfish_path) and os.path.exists(stockfish_path + ".exe"):
    stockfish_path = stockfish_path + ".exe"

Log.info(stockfish_path)
if not os.path.exists(stockfish_path):
    Log.info("Consider copying the Stockfish binaries to "
             "the ./stockfish directory of the project path.")
    Log.info("The Stockfish binary name must be exactly \"stockfish\", the file's extension removed.")
    try:
        os.mkdir(stockfish_dir)
    except FileExistsError:
        pass
    Log.error(traceback.format_exception(FileNotFoundError(stockfish_path)))
    input()
    exit(1)


def is_docker():
    return os.environ.get("hub_host", None) is not None


def execute_cmd_cdp_workaround(drv: WebDriver, cmd, params: dict):
    resource = "/session/%s/chromium/send_command_and_get_result" % drv.session_id
    url_ = drv.command_executor._url + resource
    body = json.dumps({'cmd': cmd, 'params': params})
    response = drv.command_executor._request('POST', url_, body)
    return response.get('value')


def init_remote_driver(hub_url, options_, max_retries=5, retry_delay=2):
    for _ in range(max_retries):
        try:
            return webdriver.Remote(command_executor=hub_url, options=options_)
        except:
            Log.error(traceback.format_exc(limit=2))
            sleep(retry_delay)
    raise ConnectionError


def setup_driver():
    profile_dir = os.path.join(os.getcwd(), "Profile/Selenium")
    options = Options()
    service = Service()
    options.add_argument("--mute-audio")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {
        "intl.accept_languages": ["en-US"]
    })
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en")
    options.add_argument("--accept-lang=en-US")
    
    if is_docker():
        options.add_argument("--start-maximized")
        host = os.environ["hub_host"]
        port = os.environ["hub_port"]
        Log.info(f"{host} {port}")
        chrome_driver = init_remote_driver(f"http://{host}:{port}/wd/hub", options)
        execute_cmd_cdp_workaround(chrome_driver, "Network.setUserAgentOverride", {
            "userAgent": C.user_agent
        })
    else:
        options.add_argument("--user-data-dir=" + profile_dir)
        options.add_argument("--profile-directory=Default")
        chrome_driver = webdriver.Chrome(service=service, options=options)
        chrome_driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": C.user_agent
        })
    chrome_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    Log.info(chrome_driver.execute_script("return navigator.userAgent;"))
    return chrome_driver


def trace_exec_time(func):
    def _wrapper(*a, **kw):
        t0 = time()
        res = func(*a, **kw)
        t0 = time() - t0
        Log.debug(f"<{func.__name__}> call took %.6fs" % t0)
        return res

    return _wrapper


def set_elo(engine, loop_id):
    elo = {
    }
    if loop_id in elo:
        engine.set_elo_rating(elo[loop_id])


class CustomTask(asyncio.Task):
    def __init__(self, data=None, *a, **kw):
        super().__init__(*a, **kw)
        self.data = data


async def wait_until(drv, delay_seconds: float, condition):
    async def wait_until_sub(drv_, delay_, condition_):
        return WebDriverWait(drv_, delay_).until(condition_)

    return await CustomTask(
        data=(time(), delay_seconds),
        name=C.task_wait, coro=wait_until_sub(drv, delay_seconds, condition)
    )


async def task_canceller():
    asyncio_loop = asyncio.get_event_loop()
    while asyncio_loop is None or not asyncio_loop.is_closed():
        await asyncio.sleep(3)
        try:
            if asyncio_loop is None:
                continue
            task_wait = next(filter(
                lambda x: asyncio.Task.get_name(x) == C.task_wait,
                asyncio.all_tasks(asyncio_loop)
            ), None)
            if task_wait is None:
                continue
            if not isinstance(task_wait, CustomTask):
                Log.error(f"Task {task_wait} is not an instance of {CustomTask}")
                task_wait.cancel()
                continue
            timestamp, delay = task_wait.data
            if time() - timestamp > delay + 1 and not task_wait.cancelled():
                Log.debug(f"{task_wait} is not cancellable. Unknown error, possibly a Selenium WebDriver process issue")
                task_wait.cancel()
                task_wait.cancel()
                continue
            if time() - timestamp > delay + 1:
                Log.debug(f"Attempting to cancel the task: {task_wait}")
                task_wait.cancel()
                continue
            Log.debug(f"{task_wait}")
        except asyncio.CancelledError as e:
            raise e
        except:
            Log.error(traceback.format_exc())


@trace_exec_time
def get_last_move(drv: webdriver.Chrome):
    highlighted = drv.find_elements(By.CLASS_NAME, C.highlight)

    if len(highlighted) < 2:
        Log.error("len(highlighted)<2")
        raise RuntimeError
    if len(highlighted) > 2:
        Log.error("len(highlighted)>2")
        Log.error([x.get_attribute("outerHTML") for x in highlighted])
        highlighted = highlighted[:2]

    first, second = highlighted

    def get_tile_number(e) -> int:
        return int(e.get_attribute(C.class_)[-2:])

    t1, t2 = tuple(get_tile_number(x) for x in highlighted)
    piece_xpath = C.xpath_piece % (t1, t2)
    piece = drv.find_element(By.XPATH, piece_xpath)
    if str(t1) in piece.get_attribute(C.class_):
        first, second = second, first
    f = lambda x: C.num_to_let[int(x[0])] + x[1]
    _f = lambda element: (
        f(x.lstrip(C.square)) for x in element.get_attribute(C.class_).split()
        if x.startswith(C.square)
    ).__iter__().__next__()
    tile1, tile2 = _f(first), _f(second)
    return tile1, tile2


def min_n_elements_exist(by: By, selector: typing.Any, n: int = 1):
    return lambda drv: len(drv.find_elements(by, selector)) >= n


def find_elements(by: By, selector: typing.Any, single=False):
    return lambda drv: drv.find_element(by, selector) if single else drv.find_elements(by, selector)


def find_element_and_click(by: By, selector: typing.Any):
    def find_element_and_click_sub(drv):
        try:
            element = drv.find_element(by, selector)
            element.click()
            return True
        except:
            return False

    return find_element_and_click_sub


async def handle_promotion_window(driver_):
    try:
        promotion = await wait_until(
            driver_,
            C.wait_50ms,
            EC.visibility_of_element_located((By.CLASS_NAME, C.promotion_window))
        )
        sleep(0.2)
        item = promotion.find_elements(By.CLASS_NAME, C.black_queen)
        item = item[0] if len(item) > 0 else None
        if item is None:
            item = promotion.find_elements(By.CLASS_NAME, C.white_queen)
            item = item[0] if len(item) > 0 else None
        if item is None:
            raise RuntimeError
        item.click()
    except selenium.common.exceptions.TimeoutException:
        pass
    except selenium.common.exceptions.ElementNotInteractableException:
        await handle_promotion_window(driver_)


def controls_visible(driver):
    try:
        el = driver.find_element(By.XPATH, C.new_game_buttons_xpath)
        return el.is_displayed()
    except selenium.common.exceptions.NoSuchElementException:
        return False
    except selenium.common.exceptions.StaleElementReferenceException:
        return False

def get_fen_deriv(fen: str, move_uci: str) -> str:
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)
    #assert move in board.legal_moves:
    board.push(move)
    return board.fen()

def get_next_move(engine: stockfish.Stockfish):
    global PREVIOUS_FEN_POSITIONS
    
    mv = engine.get_best_move()
    current_fen = engine.get_fen_position()
    fen_deriv = get_fen_deriv(current_fen, mv)

    if PREVIOUS_FEN_POSITIONS[fen_deriv]<2:
        PREVIOUS_FEN_POSITIONS[fen_deriv]+=1
        return mv
    
    Log.debug(f"The best move {mv} will cause a draw. Choosing another move")
    found = False
    top_moves = [x["Move"] for x in engine.get_top_moves(5)]
    print(top_moves)

    for i, mv in enumerate(top_moves):
        fen_deriv = get_fen_deriv(current_fen, mv)
        if PREVIOUS_FEN_POSITIONS[fen_deriv]<2:
            found = True
            break
        # FEN will be repeated 3 times after this move
        # the move will cause a draw

    if not found:
        mv = top_moves[0]
        Log.error(f"No move was found to prevent a draw. Playing {mv}")
        PREVIOUS_FEN_POSITIONS[get_fen_deriv(current_fen, mv)]+=1
        return mv

    PREVIOUS_FEN_POSITIONS[fen_deriv]+=1
    return mv

@trace_exec_time
async def play(driver: webdriver.Chrome, engine: stockfish.Stockfish, move):
    pos0 = C.square + str(C.let_to_num[move[0]]) + move[1]
    pos1 = C.square + str(C.let_to_num[move[2]]) + move[3]
    cls = C.space.join([C.piece, pos1, C.white_pawn, C.some_id])
    scr_rm = C.js_rm_ptr % (C.board, C.some_id)
    scr_add = C.js_add_ptr % (C.board, cls)
    driver.execute_script(scr_add)
    try:
        await wait_until(driver, C.wait_2s, find_element_and_click(
            by=By.XPATH,
            selector=f"//div[contains(@class, '{pos0}')]"
        ))
        await wait_until(driver, C.wait_2s, find_element_and_click(
            by=By.XPATH,
            selector=f"//div[contains(@class, '{C.some_id}')]"
        ))
    except selenium.common.exceptions.TimeoutException as e:
        if next_game_auto_ and not controls_visible(driver):
            driver.refresh()
            await asyncio.sleep(1)
        raise e
    driver.execute_script(scr_rm)
    engine.make_moves_from_current_position([move])
    await handle_promotion_window(driver)


async def actions(engine: stockfish.Stockfish, driver_: webdriver.Chrome):
    engine.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", True)
    PREVIOUS_FEN_POSITIONS.clear()
    if elo_rating_ > 0:
        engine.set_elo_rating(elo_rating_)

    try:
        #Log.info("Waiting for a \"board\" element")
        await wait_until(driver_, C.wait_50ms, min_n_elements_exist(
            by=By.CLASS_NAME,
            selector=C.board
        ))
        #Log.info("Waiting for the game to start")
        await wait_until(driver_, C.wait_50ms, min_n_elements_exist(
            by=By.XPATH,
            selector=C.controls_xpath,
        ))
    except selenium.common.exceptions.TimeoutException:
        return True

    timer = game_timer
    board = driver_.find_elements(By.CLASS_NAME, C.board)[0]
    Log.info(f"Board: {board}")
    driver_.execute_script(C.js_rm_ptr % (C.board, C.some_id))

    is_black = C.flipped in board.get_attribute(C.class_)
    if is_black:
        Log.info("Waiting for a \"highlight\" element")
        await wait_until(
            driver_,
            C.wait_5s,
            lambda drv: len(drv.find_elements(By.CLASS_NAME, C.highlight)) >= 2
        )

    Log.info("Is playing black pieces: %s" % is_black)

    def has_subclass(cls_lst, cls):
        return any(cls in x for x in cls_lst)

    def op_move(drv: selenium.webdriver.Chrome, last_tiles):
        cls_lst = drv.execute_script(C.scr_xpath % C.xpath_highlight)
        try:
            el = drv.find_element(By.XPATH, C.new_game_buttons_xpath)
            if el.is_displayed():
                raise RuntimeError("Game over")
        except selenium.common.exceptions.NoSuchElementException:
            pass
        except selenium.common.exceptions.StaleElementReferenceException:
            pass
        return not all(has_subclass(cls_lst, x) for x in last_tiles)


    op_move_time = 0

    async def wait_op(last_tiles) -> bool:
        nonlocal op_move_time
        t = time()
        await wait_until(driver_, C.wait_240s, lambda drv: op_move(drv, last_tiles))
        op_move_time = time() - t
        Log.debug("op_move_time = %.3f", op_move_time)
        mv = "".join(get_last_move(driver_))
        Log.info("Opponent's move: %s", mv)
        engine.make_moves_from_current_position([mv])
        return False

    def move_fmt(move_):
        return str(C.let_to_num[move_[0]]) + move_[1]

    def is_move_by_white(mv):
        return any(x in mv for x in ["1", "2", "3", "4"])

    if not is_black:
        mv_ = first_move_for_white
        await play(driver_, engine, mv_)
        by_w_ = is_move_by_white(mv_)
        Log.info("Is last move by white: %s" % by_w_)
        if await wait_op([C.square + move_fmt(mv_[:2]), C.square + move_fmt(mv_[2:4])]):
            return True
    else:
        engine.make_moves_from_current_position(["".join(get_last_move(driver_))])

    @trace_exec_time
    def next_move(engine_: stockfish.Stockfish):
        return get_next_move(engine=engine_)

    last_wt = 0.0

    def get_move_delay(stockfish_time) -> float:
        nonlocal move, last_wt
        r_ = elo_rating_ if elo_rating_ > 0 else 2500
        is_capturing = engine.get_what_is_on_square(move[2:4])
        piece = engine.get_what_is_on_square(move[:2])
        is_pawn = piece == stockfish.Stockfish.Piece.BLACK_PAWN or piece == stockfish.Stockfish.Piece.WHITE_PAWN
        if is_capturing or is_pawn:
            last_wt = max(0.0, last_wt - last_wt / random.randint(1, 3) - 2)
            return abs(random.random() / 2) * r_ / 2500 + 0.1
        wt_ = random.randint(0, 200) * random.randint(0, 1)
        if last_wt != 0:
            last_wt = max(0.0, last_wt - last_wt / random.randint(1, 3) - 2)
            return max(0.0, (abs(random.random() / 4) + op_move_time * abs(
                random.random() / 2)) * game_timer / 60000 * r_ / 2500)
        wt_ = wt_ if wt_ > 0 else random.randint(1000, 3000)
        wt_ = min(wt_ * stockfish_time * 6, timer // 8) / 1000
        wt_ = min(random.randint(2, 7), wt_)
        last_wt = wt_ if last_wt == 0 else last_wt
        return (wt_ + op_move_time * abs(random.random() / 2) + abs(
            random.random() / 2)) * game_timer / 60000 * r_ / 2500

    for loop_id in itertools.count():
        t_ = time()
        set_elo(engine, loop_id)
        move = next_move(engine)
        t_ = time() - t_
        Log.info("Next move: %s", move)
        wt = 0
        if move_delay:
            wt = get_move_delay(t_) * MOVE_DELAY_MULTIPLIER
            wt = wt if loop_id > 4 else max(wt, abs(random.random() / 3) + 0.1)
            Log.debug("wt=%.3f last_wt=%.3f", wt, last_wt)
            sleep(wt)
        timer = max(0.0, timer - (wt + t_) * 1000)
        Log.debug("timer = " + str(timer))
        try:
            await play(driver_, engine, move)
        except selenium.common.exceptions.ElementClickInterceptedException:
            pass
        cls1 = C.square + str(C.let_to_num[move[0]]) + move[1]
        cls2 = C.square + str(C.let_to_num[move[2]]) + move[3]
        Log.info("Waiting for opponent's move")
        if await wait_op([cls1, cls2]):
            return True
    return False


async def main_():
    driver = setup_driver()
    engine = stockfish.Stockfish(path=os.path.join(os.getcwd(), stockfish_path))

    async def stop_event_loop():
        Log.debug("Stopping the event loop...")
        asyncio_loop = asyncio.get_event_loop()
        while asyncio_loop.is_running():
            asyncio_loop.stop()
            await asyncio.sleep(0.5)
        driver.quit()
        executor.shutdown(cancel_futures=True)

    async def handle_menu_buttons(wait):
        global NEW_GAME_BUTTON_CLICK_TIME
        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@id="guest-button"]'))).click()
            await asyncio.sleep(0.5)
        except selenium.common.exceptions.TimeoutException:
            pass
        try:
            new_game_buttons = wait.until(EC.visibility_of_element_located((By.XPATH, C.new_game_buttons_xpath)))
            await asyncio.sleep(0.5)
        except selenium.common.exceptions.TimeoutException:
            return
        try:
            _ = new_game_buttons.find_element(By.XPATH, C.new_game_button_sub_xpath % "Decline")
            await asyncio.sleep(0.5)
            _.click()
        except selenium.common.exceptions.WebDriverException:
            pass
        try:
            _ = new_game_buttons.find_element(By.XPATH, C.new_game_button_sub_xpath % "New")
            await asyncio.sleep(0.5)
            _.click()
            NEW_GAME_BUTTON_CLICK_TIME=time()
        except selenium.common.exceptions.WebDriverException:
            pass
        
        if time()-NEW_GAME_BUTTON_CLICK_TIME>NEW_GAME_BUTTON_CLICK_TIMEOUT:
            # Sometimes, the "New Game" button does not start a new game 
            # possibly due to a chess.com server related matchmaking bug or network issues.
            # The driver will be refreshed in such cases
            driver.refresh()
            NEW_GAME_BUTTON_CLICK_TIME=time()
            await asyncio.sleep(1)

    async def handle_driver_exc(e):
        try:
            driver.quit()
        except:
            Log.error(traceback.format_exc())
        await stop_event_loop()
        raise e

    async def loop():
        try:
            return await actions(engine, driver)
        except KeyboardInterrupt as e:
            await stop_event_loop()
            raise e
        except selenium.common.exceptions.NoSuchWindowException as e:
            Log.error(traceback.format_exc())
            await handle_driver_exc(e)
        except:
            Log.error(traceback.format_exc())
            await asyncio.sleep(1)
            return True

    driver.get(url)
    asyncio.create_task(task_canceller())
    wait_ = WebDriverWait(driver, 0.1)
    while await loop():
        if next_game_auto_ and "computer" not in driver.current_url:
            await handle_menu_buttons(wait_)
        await asyncio.sleep(0.1)

    Log.info("Closing Selenium WebDriver in %s seconds" % C.exit_delay)
    sleep(C.exit_delay)
    driver.quit()


def main(elo_rating=-1, game_timer_ms: int = 300000,
         first_move_w: str = "e2e4",
         enable_move_delay: bool = False,
         next_game_auto: str = "True"):
    global game_timer, first_move_for_white
    global move_delay, elo_rating_, next_game_auto_

    game_timer = int(game_timer_ms)
    first_move_for_white = first_move_w

    move_delay = enable_move_delay
    elo_rating_ = int(elo_rating)
    next_game_auto_ = next_game_auto[0].lower() == "t"

    def main_ev_loop():
        ev_loop = asyncio.new_event_loop()
        ev_loop.set_default_executor(executor)
        ev_loop.run_until_complete(main_())

    if not is_docker():
        main_ev_loop()
    else:
        while 1:
            thr = threading.Thread(target=main_ev_loop, daemon=True)
            thr.start()
            thr.join()


def main_docker():
    kw = dict(filter(lambda _: _[1] is not None, ((arg, os.environ.get(arg, None)) for arg in [
        "elo_rating", "game_timer_ms", "first_move_w",
        "enable_move_delay"])))
    Log.debug(f"kwargs: {kw}")
    main(**kw)


if __name__ == '__main__' and not is_docker():
    typer.run(main)
elif __name__ == '__main__':
    main_docker()
