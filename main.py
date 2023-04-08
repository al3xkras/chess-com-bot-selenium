import os
from time import time, sleep

import numpy as np
import selenium.webdriver.common.devtools.v106 as devtools
import stockfish
import trio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

import platform

if "win" in platform.platform().lower():
    stockfish_path = "/stockfish/stockfish"
elif "linux" in platform.platform().lower():
    stockfish_path = "/stockfish/stockfish"
else:
    raise Exception("platform not supported: %s"%platform.platform())

url = "https://www.chess.com/play/computer"
ask_confirmation=True

num_to_let = dict(zip(range(1, 9), "abcdefgh"))
let_to_num = dict(zip("abcdefgh", range(1, 9)))

location_override = {
    "latitude":48.8781,
    "longitude":-28.6298
}

moves_limit = 150

class C:
    board="board"
    flipped="flipped"
    outerHTML="outerHTML"
    square="square-"
    piece="piece"
    highlight="highlight"
    class_="class"
    some_id="p1234"
    promotion_moves=["1","8"]

class Log:
    @staticmethod
    def info(*o):
        print(*o)

    @staticmethod
    def error(o):
        print(o)


def setup_driver(profile_path=None):
    options = Options()
    headless = False
    profile_dir = os.getcwd() + "/Profile/Selenium"

    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-web-security")
    options.add_argument("--mute-audio")
    # options.set_capability("acceptInsecureCerts",True)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--start-maximized")
    # options.addExtensions(new File("./adblock.crx"));
    # options.add_argument("--disable-popup-blocking")
    if headless:
        options.add_argument("--headless")

    if profile_dir:
        options.add_argument("--user-data-dir=" + profile_dir)
        options.add_argument("--profile-directory=Default")

    chrome_driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    chrome_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    chrome_driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36"
    })

    Log.info(chrome_driver.execute_script("return navigator.userAgent;"))

    return chrome_driver


def get_last_move(driver: webdriver.Chrome):

    pieces_ = driver.find_elements(By.CLASS_NAME, C.piece)
    Log.info("pieces: ", pieces_)
    highlighted = driver.find_elements(By.CLASS_NAME, C.highlight)
    Log.info("highlighted: ", highlighted)

    if len(highlighted) < 2:
        Log.error("len(highlighted)<2")
        return None
    if len(highlighted) > 2:
        Log.error("len(highlighted)>2")

    first, second = highlighted
    for piece in pieces_:
        for cls in piece.get_attribute(C.class_).split():
            if cls.startswith(C.square) and cls in first.get_attribute(C.class_):
                first, second = second, first
                break
            elif cls.startswith(C.square) and cls in second.get_attribute(C.class_):
                break

    f = lambda x: num_to_let[int(x[0])] + x[1]

    tile1 = [f(x.lstrip(C.square)) for x in first.get_attribute(C.class_).split() if x.startswith(C.square)][0]
    tile2 = [f(x.lstrip(C.square)) for x in second.get_attribute(C.class_).split() if x.startswith(C.square)][0]
    # piece_type = [x for x in second.get_attribute(C.class_).split() if len(x)==2][0]
    # move_by,piece_type=piece_type[0],piece_type[1]
    return tile1, tile2  # ,piece_type

def play(driver: webdriver.Chrome, wait: WebDriverWait, engine: stockfish.Stockfish, move):
    engine.make_moves_from_current_position([move])

    pos0 = move[:2]
    pos1 = move[2:]
    pos0 = C.square + str(let_to_num[pos0[0]]) + pos0[1]
    pos1 = C.square + str(let_to_num[pos1[0]]) + pos1[1]

    cls = " ".join([C.piece, pos1, "wp", C.some_id])

    Log.info("adding board item")
    scr = """
    var board = document.getElementsByClassName('%s').item(0);
    var piece = document.createElement('div');

    piece.setAttribute('class', '%s');
    board.appendChild(piece);
    """ % (C.board,cls)
    driver.execute_script(scr)
    Log.info("board item added")

    Log.info("Playing next move...")
    # sleep(1)
    e0 = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, pos0)))
    e0.click()
    Log.info("First clicked...")
    # sleep(0.1)
    e1 = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, C.some_id)))
    e1.click()
    Log.info("Second clicked...")
    # sleep(1)
    Log.info("The move is played")
    Log.info("Removing the pointer...")
    scr1 = """
    var board = document.getElementsByClassName('board').item(0);
    var to_rm = document.getElementsByClassName('%s').item(0);
    board.removeChild(to_rm)
    """%C.some_id
    driver.execute_script(scr1)
    Log.info("waiting...")
    # sleep()
    Log.info("next move")


def actions(driver: webdriver.Chrome, session):

    driver.get(url)
    wait = WebDriverWait(driver, 120)
    if ask_confirmation:
        input("Press any key when you're ready to play")
    Log.info("Waiting for the board...")
    wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, C.board))
    )
    Log.info("Chess board found")
    sleep(2)
    board = driver.find_elements(By.CLASS_NAME, C.board)[0]

    is_black = C.flipped in board.get_attribute(C.class_)
    # Log.info("contents: ",board.get_attribute(C.flipped))
    Log.info("Is playing black pieces: %s" % is_black)

    engine = stockfish.Stockfish(path=os.getcwd()+stockfish_path)
    engine.set_fen_position(
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", True
    )

    if is_black:
        Log.info("Waiting for a \"highlight\" element")
        wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, C.highlight))
        )
        Log.info("Element found")
        t1, t2 = get_last_move(driver)
        Log.info("Previous move:", t1 + t2)
        engine.make_moves_from_current_position([t1 + t2])
    else:
        t1, t2 = None, None
    last_move = t1
    loop_id = 0
    btime = None
    time_std = 680
    time_avg = 550
    while loop_id < moves_limit:
        loop_id += 1
        move = engine.get_best_move(btime=btime)
        Log.info("Playing the next move: ", move)
        play(driver, wait, engine, move)
        last_move = str(let_to_num[move[0]]) + move[1]

        cls = C.square + last_move

        piece = driver.find_element(By.CLASS_NAME, cls)
        state = piece.get_attribute(C.outerHTML)
        Log.info("The move is played")
        Log.info("Waiting for opponent's move")
        op_time = time()
        sleep(0.1)
        wait.until(lambda drv: drv.find_element(By.CLASS_NAME, cls).get_attribute(C.outerHTML) != state)
        op_time = time() - op_time
        btime = op_time + abs(np.random.random()) * time_std + time_avg
        sleep(0.1)
        t1, t2 = get_last_move(driver)
        last_move = t2
        move_ = t1 + t2

        Log.info("Opponent's move: ", move_)
        try:
            engine.make_moves_from_current_position([move_])
        except ValueError:
            if move_[3] in C.promotion_moves:
                Log.error("not implemented")
                #move_ += "q"
            engine.make_moves_from_current_position([move_])

if __name__ == '__main__':
    async def main():
        driver = setup_driver()
        async with driver.bidi_connection() as session:
            Log.info("Selenium CDP session open")
            cdpSession = session.session
            await cdpSession.execute(
                devtools.emulation.set_geolocation_override(**location_override, accuracy=95))
            actions(driver, session)
            s=10
            Log.info("Closing Selenium WebDriver in %s seconds"%s)
            sleep(s)
            driver.quit()

    trio.run(main)
