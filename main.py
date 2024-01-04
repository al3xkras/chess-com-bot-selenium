import os
import random
import sys
import traceback
from time import time, sleep

import logging
import selenium.common.exceptions
import selenium.webdriver.common.devtools.v114 as devtools
import trio
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
    board_xpath = "//div[@class='small-controls-rightIcons' or @class='live-game-buttons-component']"
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
    Log.info("The Stockfish binary name, must not contain a file extension, e.g. .exe/.sh")
    os.mkdir(stockfish_dir)
    raise FileNotFoundError(stockfish_path)


def setup_driver():
    profile_dir = os.getcwd() + "/Profile/Selenium"
    options = Options()
    service = Service()
    options.add_argument("--mute-audio")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-data-dir=" + profile_dir)
    options.add_argument("--profile-directory=Default")
    chrome_driver = webdriver.Chrome(service=service, options=options)
    chrome_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    chrome_driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": C.user_agent
    })
    Log.info(chrome_driver.execute_script("return navigator.userAgent;"))
    return chrome_driver

def get_last_move(driver: webdriver.Chrome):
    t_ = time()
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
    t_ = time() - t_
    Log.debug("get_last_move took %.5f" % t_)
    return tile1, tile2


def play(driver: webdriver.Chrome, wait: WebDriverWait, engine: stockfish.Stockfish, move):
    t_ = time()
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
    e0 = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, pos0)))
    e0.click()
    e1 = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, C.some_id)))
    e1.click()
    driver.execute_script(scr_rm)
    w = WebDriverWait(driver, 0.05)
    try:
        window = w.until(EC.visibility_of_element_located((By.CLASS_NAME, C.promotion_window)))
        sleep(0.2)
        items = window.find_elements(By.CLASS_NAME, C.black_queen)
        if len(items) == 0:
            items = window.find_elements(By.CLASS_NAME, C.white_queen)
        items[0].click()
    except selenium.common.exceptions.TimeoutException:
        pass
    t_ = time() - t_
    Log.debug("play took %.5f" % t_)


def actions(engine: stockfish.Stockfish, driver: webdriver.Chrome, session):
    global timer_
    engine.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", True)
    if elo_rating_ > 0:
        engine.set_elo_rating(elo_rating_)
    wait = WebDriverWait(driver, 120)
    wait_5s = WebDriverWait(driver, 5)
    wait_1s = WebDriverWait(driver, 1)

    game_over = False

    if not first_move_autoplay:
        Log.info("Waiting for a \"highlight\" element")
        wait_5s.until(
            lambda drv: len(drv.find_elements(By.CLASS_NAME, C.highlight)) >= 2
        )
    else:
        try:
            Log.info("Waiting for the \"board\"")
            wait_5s.until(
                EC.element_to_be_clickable((By.CLASS_NAME, C.board))
            )
            Log.info("Waiting for the game to start")
            wait_5s.until(
                EC.element_to_be_clickable((By.XPATH, C.board_xpath))
            )
        except selenium.common.exceptions.TimeoutException:
            return True

    board = driver.find_elements(By.CLASS_NAME, C.board)[0]
    Log.info("Chess board found")
    timer_ = game_timer

    is_black = C.flipped in board.get_attribute(C.class_)
    if is_black:
        Log.info("Waiting for a \"highlight\" element")
        wait_5s.until(
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

    def wait_op(last_tiles) -> bool:
        nonlocal game_over, op_move_time
        t1_ = time()
        wait.until(lambda drv: op_move(drv, last_tiles))
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
        try:
            engine.make_moves_from_current_position([move_])
        except ValueError:
            Log.error(engine.get_fen_position())
            try:
                if not move_.endswith(C.promotion_move_queen):
                    make_move(move_ + C.promotion_move_queen)
                    return
            except ValueError:
                pass
            move_ = move_[2:4] + move_[:2]
            engine.make_moves_from_current_position([move_])

    def move_fmt(move_):
        return str(C.let_to_num[move_[0]]) + move_[1]

    def is_move_by_white(mv):
        w = ["1", "2", "3", "4"]
        return any(x in mv for x in w)

    if not is_black:
        play(driver, wait_1s, engine, first_move_if_playing_white)
        t1, t2 = get_last_move(driver)
        by_w_ = is_move_by_white(t1)
        Log.info("Is last move played by white: %s" % by_w_)
        if by_w_:
            if not first_move_autoplay:
                engine.make_moves_from_current_position([t1 + t2])
            if wait_op([C.square + move_fmt(t1), C.square + move_fmt(t2)]):
                return True
        else:
            engine.make_moves_from_current_position([first_move_if_playing_white, t1 + t2])

    else:
        t1, t2 = get_last_move(driver)
        engine.make_moves_from_current_position([t1 + t2])

    def next_move(engine_: stockfish.Stockfish):
        _ = time()
        mv = engine_.get_best_move()
        _ = time() - _
        Log.info("next_move took %.5f" % _)
        return mv

    last_wt = 0.0
    Piece = stockfish.Stockfish.Piece

    def get_move_delay(stockfish_time) -> float:
        nonlocal move, last_wt
        r_ = elo_rating_ if elo_rating_ > 0 else 2500
        is_capturing = engine.get_what_is_on_square(move[2:4])
        piece = engine.get_what_is_on_square(move[:2])
        is_pawn = piece == stockfish.Stockfish.Piece.BLACK_PAWN or piece == stockfish.Stockfish.Piece.WHITE_PAWN
        if is_capturing or is_pawn:
            last_wt = max(0.0, last_wt - last_wt / random.randint(1, 3) - 2)
            return abs(random.random() / 3) * r_ / 2500

        wt_ = random.randint(0, 200) * random.randint(0, 1)
        if last_wt != 0:
            last_wt = max(0.0, last_wt - last_wt / random.randint(1, 3) - 2)
            return max(0.0, (abs(random.random() / 4) + op_move_time * abs(random.random() / 2)) * game_timer / 60000 * r_ / 2500)

        wt_ = wt_ if wt_ != 0 else random.randint(1000, 3000)
        wt_ = min(wt_ * stockfish_time * 6, timer_ // 8) / 1000
        wt_ = min(random.randint(2, 7), wt_)
        if last_wt == 0:
            last_wt = wt_
        #preventing passing a negative time (last_wt)
        return max(0.0, (wt_ + op_move_time * abs(random.random() / 2) + abs(random.random() / 2)) * game_timer / 60000 * r_ / 2500)

    loop_id = 0

    while loop_id < moves_limit:
        loop_id += 1
        t_ = time()
        move = next_move(engine)
        t_ = time() - t_
        wt = 0
        Log.info("Playing next move: %s", move)
        if move_delay:
            wt = get_move_delay(t_)
            Log.debug("wt=%.3f last_wt=%.3f", wt, last_wt)
            sleep(wt)
        timer_ -= (wt + t_) * 1000
        try:
            play(driver, wait_1s, engine, move)
        except selenium.common.exceptions.ElementClickInterceptedException:
            game_over = True
        tile1 = str(C.let_to_num[move[0]]) + move[1]
        tile2 = str(C.let_to_num[move[2]]) + move[3]
        cls1 = C.square + tile1
        cls2 = C.square + tile2
        Log.info("Waiting for opponent's move")
        if wait_op([cls1, cls2]):
            return True
    return False


async def main0():
    driver = setup_driver()
    async with driver.bidi_connection() as session:
        engine = stockfish.Stockfish(path=os.getcwd() + stockfish_path)
        Log.info("Selenium CDP session open")
        cdpSession = session.session
        if location_override:
            await cdpSession.execute(
                devtools.emulation.set_geolocation_override(**location, accuracy=95))

        def loop():
            try:
                return actions(engine, driver, session)
            except Exception as e:
                if isinstance(e, KeyboardInterrupt):
                    raise e
                exc = traceback.format_exc()
                print(exc)
                return True

        driver.get(url)
        while loop():
            sleep(0.5)
        s = 10
        Log.info("Closing Selenium WebDriver in %s seconds" % s)
        sleep(s)
        driver.quit()


def main(elo_rating=-1, game_timer_ms: int = 300000, first_move_w: str = "e2e4", enable_move_delay: bool = False,
         override_location=True,
         location_lat: float = 48.8781,
         location_lon: float = -28.6298):
    global game_timer, first_move_if_playing_white, first_move_autoplay
    global move_delay, moves_limit, location, location_override, elo_rating_, timer_

    game_timer = int(game_timer_ms)
    timer_ = game_timer
    first_move_autoplay = first_move_w is not None and len(first_move_w) == 4
    first_move_if_playing_white = first_move_w

    move_delay = enable_move_delay
    moves_limit = 350
    location_override = bool(override_location)
    elo_rating_ = int(elo_rating)

    location = {
        "latitude": float(location_lat),
        "longitude": float(location_lon)
    }
    trio.run(main0)


if __name__ == '__main__':
    typer.run(main)
