import asyncio
import os
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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import stockfish

url = "https://www.chess.com/"
stockfish_dir = "./stockfish"
stockfish_path = stockfish_dir + "/stockfish"
asyncio_loop = None


class C:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
                 "(KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36"
    board = "board"
    flipped = "flipped"
    outerHTML = "outerHTML"
    square = "square-"
    piece = "piece"
    hover = "hover-"
    highlight = "highlight"
    class_ = "class"
    space = " "
    controls_xpath = "//div[@class='game-controls-controller-component' or @class='live-game-buttons-component']"
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
    wait_120s = 120
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


def setup_driver():
    profile_dir = os.getcwd() + "/Profile/Selenium"
    options = Options()
    service = Service()
    options.add_argument("--mute-audio")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    import json

    def execute_cmd_cdp_workaround(drv, cmd, params: dict):
        resource = "/session/%s/chromium/send_command_and_get_result" % drv.session_id
        url_ = drv.command_executor._url + resource
        body = json.dumps({'cmd': cmd, 'params': params})
        response = drv.command_executor._request('POST', url_, body)
        return response.get('value')

    def init_remote_driver(hub_url, options_, max_retries=5, retry_delay=2):
        for _ in range(max_retries):
            try:
                driver = webdriver.Remote(command_executor=hub_url, options=options_)
                return driver
            except:
                Log.error(traceback.format_exc(limit=2))
                sleep(retry_delay)
        raise ConnectionError

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


class CustomTask(asyncio.Task):
    def __init__(self, data=None, *a, **kw):
        super().__init__(*a, **kw)
        self.data = data


async def wait_until(drv, delay_seconds: float, condition):
    async def wait_until_sub(drv_, delay_, condition_):
        return WebDriverWait(drv_, delay_).until(condition_)

    return await CustomTask(
        data=(time(), delay_seconds),
        name=C.task_wait, coro=asyncio.wait_for(
            wait_until_sub(drv, delay_seconds, condition),
            delay_seconds + 1,
        ))


def task_canceller_thread():
    global asyncio_loop
    while 1:
        try:
            sleep(2)
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
                Log.debug(f"{task_wait} cancellation is taking too long ")
                task_wait.cancel()
                task_wait.cancel()
                task_wait.cancel()
                continue
            if time() - timestamp > delay + 1:
                Log.debug(f"Attempting to cancel the task: {task_wait}")
                task_wait.cancel()
                continue
            Log.debug(f"{task_wait}")
        except:
            Log.error(traceback.format_exc())


threading.Thread(daemon=True, target=task_canceller_thread).start()


@trace_exec_time
def get_last_move(driver: webdriver.Chrome):
    highlighted = driver.find_elements(By.CLASS_NAME, C.highlight)

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
    piece = driver.find_element(By.XPATH, piece_xpath)
    assert piece
    if str(t1) in piece.get_attribute(C.class_):
        first, second = second, first
    f = lambda x: C.num_to_let[int(x[0])] + x[1]
    _f = lambda element: (
        f(x.lstrip(C.square)) for x in element.get_attribute(C.class_).split()
        if x.startswith(C.square)
    ).__iter__().__next__()
    tile1, tile2 = _f(first), _f(second)
    return tile1, tile2


async def sleep_async(delay):
    await asyncio.sleep(delay)


@trace_exec_time
async def play(driver: webdriver.Chrome, engine: stockfish.Stockfish, move):
    engine.make_moves_from_current_position([move])
    pos0 = move[:2]
    pos1 = move[2:]
    pos0 = C.square + str(C.let_to_num[pos0[0]]) + pos0[1]
    pos1 = C.square + str(C.let_to_num[pos1[0]]) + pos1[1]
    cls = C.space.join([C.piece, pos1, C.white_pawn, C.some_id])
    scr_rm = C.js_rm_ptr % (C.board, C.some_id)
    scr_add = C.js_add_ptr % (C.board, cls)
    driver.execute_script(scr_rm)
    driver.execute_script(scr_add)
    e0 = await wait_until(driver, C.wait_2s, EC.element_to_be_clickable((By.CLASS_NAME, pos0)))
    e0.click()
    e1 = await wait_until(driver, C.wait_2s, EC.element_to_be_clickable((By.CLASS_NAME, C.some_id)))
    e1.click()
    driver.execute_script(scr_rm)
    try:
        promotion = await wait_until(driver, C.wait_50ms,
                                     EC.visibility_of_element_located((By.CLASS_NAME, C.promotion_window)))
        sleep(0.2)
        items = promotion.find_elements(By.CLASS_NAME, C.black_queen)
        if len(items) == 0:
            items = promotion.find_elements(By.CLASS_NAME, C.white_queen)
        items[0].click()
    except selenium.common.exceptions.TimeoutException:
        pass


async def actions(engine: stockfish.Stockfish, driver: webdriver.Chrome):
    global timer_
    engine.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", True)
    if elo_rating_ > 0:
        engine.set_elo_rating(elo_rating_)

    game_over = False

    def min_n_elements_exist(by: By, selector: typing.Any, n: int = 1):
        return lambda drv: len(drv.find_elements(by, selector)) >= n

    if not first_move_autoplay:
        Log.info("Waiting for a \"highlight\" element")
        await wait_until(driver, C.wait_5s, min_n_elements_exist(
            by=By.CLASS_NAME,
            selector=C.highlight,
            n=2
        ))
    else:
        try:
            Log.info("Waiting for a \"board\" element")
            await wait_until(driver, C.wait_5s, min_n_elements_exist(
                by=By.CLASS_NAME,
                selector=C.board
            ))
            Log.info("Waiting for the game to start")
            await wait_until(driver, C.wait_5s, min_n_elements_exist(
                by=By.XPATH,
                selector=C.controls_xpath,
            ))
        except selenium.common.exceptions.TimeoutException:
            return True

    board = driver.find_elements(By.CLASS_NAME, C.board)[0]
    Log.info("Board found")
    timer_ = game_timer

    is_black = C.flipped in board.get_attribute(C.class_)
    if is_black:
        Log.info("Waiting for a \"highlight\" element")
        await wait_until(driver, C.wait_5s,
                         lambda drv: len(drv.find_elements(By.CLASS_NAME, C.highlight)) >= 2
                         )

    Log.info("Is playing black pieces: %s" % is_black)

    def f(cls_lst, cls):
        return any(cls in x for x in cls_lst)

    def op_move(drv: selenium.webdriver.Chrome, last_tiles):
        nonlocal game_over
        cls_lst = drv.execute_script(C.scr_xpath % C.xpath_highlight)
        return game_over or not all(f(cls_lst, x) for x in last_tiles)

    op_move_time = 0

    async def wait_op(last_tiles) -> bool:
        nonlocal game_over, op_move_time
        t1_ = time()
        await wait_until(driver, C.wait_120s, lambda drv: op_move(drv, last_tiles))
        op_move_time = time() - t1_
        Log.debug("op_move_time = %.3f", op_move_time)
        if game_over:
            Log.info("game over")
            return True
        move_ = "".join(get_last_move(driver))
        Log.info("Opponent's move: %s", move_)
        make_move(move_)
        return False

    def make_move(move_):
        if len(move_) == 5:
            assert move_.endswith(C.promotion_move_queen)
            try:
                engine.make_moves_from_current_position([move_])
            except ValueError:
                Log.error(move_ + " " + engine.get_fen_position())
                engine.make_moves_from_current_position([move_[2:4] + move_[:2] + move_[4]])
            return
        assert len(move_) == 4

        def resolve_move_exception(move, on_exception=None):
            try:
                engine.make_moves_from_current_position([move])
            except ValueError:
                Log.error(move + " " + engine.get_fen_position())
                None if not on_exception else on_exception()

        resolve_move_exception(
            move=move_,
            on_exception=lambda: resolve_move_exception(
                move=move_[2:4] + move_[:2],
                on_exception=lambda: resolve_move_exception(
                    move=move_ + C.promotion_move_queen,
                    on_exception=lambda: resolve_move_exception(
                        move=move_[2:4] + move_[:2] + C.promotion_move_queen
                    )
                )
            )
        )

    def move_fmt(move_):
        return str(C.let_to_num[move_[0]]) + move_[1]

    def is_move_by_white(mv):
        return any(x in mv for x in list(map(str, range(1, 5))))

    if not is_black:
        await play(driver, engine, first_move_if_playing_white)
        t1, t2 = get_last_move(driver)
        by_w_ = is_move_by_white(t1)
        Log.info("Last move by white: %s" % by_w_)
        if by_w_:
            if not first_move_autoplay:
                engine.make_moves_from_current_position([t1 + t2])
            if await wait_op([C.square + move_fmt(t1), C.square + move_fmt(t2)]):
                return True
        else:
            engine.make_moves_from_current_position([first_move_if_playing_white, t1 + t2])

    else:
        t1, t2 = get_last_move(driver)
        engine.make_moves_from_current_position([t1 + t2])

    @trace_exec_time
    def next_move(engine_: stockfish.Stockfish):
        return engine_.get_best_move()

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
        wt_ = min(wt_ * stockfish_time * 6, timer_ // 8) / 1000
        wt_ = min(random.randint(2, 7), wt_)
        last_wt = wt_ if last_wt == 0 else last_wt
        return (wt_ + op_move_time * abs(random.random() / 2) + abs(
            random.random() / 2)) * game_timer / 60000 * r_ / 2500

    loop_id = 0

    while loop_id < moves_limit:
        loop_id += 1
        t_ = time()
        move = next_move(engine)
        t_ = time() - t_
        wt = 0
        Log.info("Next move: %s", move)
        if move_delay:
            wt = get_move_delay(t_)
            wt = wt if loop_id > 4 else max(wt, abs(random.random() / 3) + 0.1)
            Log.debug("wt=%.3f last_wt=%.3f", wt, last_wt)
            sleep(wt)
        timer_ = max(0.0, timer_ - (wt + t_) * 1000)
        Log.debug("timer = " + str(timer_))
        try:
            await play(driver, engine, move)
        except selenium.common.exceptions.ElementClickInterceptedException:
            game_over = True
        tile1 = str(C.let_to_num[move[0]]) + move[1]
        tile2 = str(C.let_to_num[move[2]]) + move[3]
        cls1 = C.square + tile1
        cls2 = C.square + tile2
        Log.info("Waiting for opponent's move")
        if await wait_op([cls1, cls2]):
            return True
    return False


async def main0():
    global asyncio_loop
    driver = setup_driver()
    engine = stockfish.Stockfish(path=os.path.join(os.getcwd(), stockfish_path))
    asyncio_loop = asyncio.get_event_loop()
    async def loop():
        try:
            return await actions(engine, driver)
        except KeyboardInterrupt as e:
            raise e
        except selenium.common.exceptions.NoSuchWindowException as e:
            raise e
        except:
            Log.error(traceback.format_exc())
            return True

    driver.get(url)
    while await loop():
        await sleep_async(0.5)

    Log.info("Closing Selenium WebDriver in %s seconds" % C.exit_delay)
    sleep(C.exit_delay)
    driver.quit()


def main(elo_rating=-1, game_timer_ms: int = 300000,
         first_move_w: str = "e2e4",
         enable_move_delay: bool = False):
    global game_timer, first_move_if_playing_white, first_move_autoplay
    global move_delay, moves_limit, elo_rating_, timer_

    game_timer = int(game_timer_ms)
    timer_ = game_timer
    first_move_autoplay = first_move_w is not None and len(first_move_w) == 4
    first_move_if_playing_white = first_move_w

    move_delay = enable_move_delay
    moves_limit = 350
    elo_rating_ = int(elo_rating)

    asyncio.run(main0())


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
