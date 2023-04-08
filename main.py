import os
from time import time, sleep

import numpy as np
import selenium.common.exceptions
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
ask_confirmation=False

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
    _debug=False

    @staticmethod
    def info(*o):
        print(*o)

    @staticmethod
    def error(*o):
        print(o)

    @classmethod
    def debug(cls,*o):
        if cls._debug:
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
    Log.debug("pieces: ", pieces_)
    highlighted = driver.find_elements(By.CLASS_NAME, C.highlight)
    Log.debug("highlighted: ", highlighted)

    if len(highlighted) < 2:
        Log.error("len(highlighted)<2")
        return "",""
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
    #sleep(0.05)
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

    w = WebDriverWait(driver, 0.05)
    try:
        window = w.until(EC.visibility_of_element_located((By.CLASS_NAME, "promotion-window")))
        sleep(0.2)
        items = window.find_elements(By.CLASS_NAME, "bq")
        if len(items)==0:
            items = window.find_elements(By.CLASS_NAME, "wq")
        items[0].click()
    except selenium.common.exceptions.TimeoutException:
        pass

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
    game_over = False
    wait_10ms=WebDriverWait(driver,0.01)

    Log.info("Waiting for a \"highlight\" element")
    wait.until(
        lambda drv:len(drv.find_elements(By.CLASS_NAME, C.highlight))>=2
    )
    t1, t2 = get_last_move(driver)
    engine.make_moves_from_current_position([t1+t2])

    def f(elements, cls):
        return any(cls in x.get_attribute(C.outerHTML) for x in elements)

    def op_move(drv: selenium.webdriver.Chrome,last_tiles):
        nonlocal game_over
        try:
            modal1 = "board-modal-modal"
            modal2 = "game-over-modal"
            xpath = "//div[@class='%s' or @id='%s']" % (modal1, modal2)
            wait_10ms.until(EC.visibility_of_element_located((By.XPATH, xpath)))

            game_over = True
        except selenium.common.exceptions.TimeoutException:
            pass
        elements = drv.find_elements(By.CLASS_NAME, C.highlight)
        return game_over or not (f(elements, last_tiles[0]) and f(elements, last_tiles[1]))

    def wait_op(last_tiles) -> bool:
        wait.until(lambda drv: op_move(drv,last_tiles))
        if game_over:
            Log.info("game over")
            return True
        # op_time = time() - op_time
        # btime = abs(np.random.normal(loc=max(0,time_avg-btime),scale=op_time*time_std))
        sleep(0.1)
        t1, t2 = get_last_move(driver)
        move_ = t1 + t2

        Log.info("Opponent's move: ", move_)
        try:
            engine.make_moves_from_current_position([move_])
        except ValueError:
            if move_[3] in C.promotion_moves:
                Log.error("not implemented")
                # move_ += "q"
            engine.make_moves_from_current_position([move_])
        return False

    if not is_black:
        if wait_op([C.square+t1,C.square+t2]):
            return True

    loop_id = 0
    #btime = 1000
    #time_std = 750
    #time_avg = 350
    while loop_id < moves_limit:
        loop_id += 1
        #t=time()
        #m_count=2
        n_moves=4
        p = np.array([1/loop_id**(_-1.2) for _ in range(1,n_moves+1)])
        p /= np.sum(p)
        print(p)
        i = np.random.choice([0, 1, 2, 3], p=p)
        w=np.random.choice([1,1.3,2,2],p=[0.6,0.2,0.1,0.1])
        if i-1>0:
            sleep((i-1)*w)
        Log.info(i)
        #print(i)
        move = engine.get_top_moves(i+1)[::-1][0]['Move'] if i>0 else engine.get_best_move()
        #t=time()-t
        #sleep(max(0,(i+1)*(btime-t*1000)/1000))
        Log.info("Playing next move: ", move)
        try:
            play(driver, wait, engine, move)
        except selenium.common.exceptions.ElementClickInterceptedException:
            game_over=True
        tile1 = str(let_to_num[move[0]]) + move[1]
        tile2 = str(let_to_num[move[2]]) + move[3]
        cls1 = C.square + tile1
        cls2 = C.square + tile2

        Log.info("The move is played")
        Log.info("Waiting for opponent's move")
        sleep(0.1)

        if wait_op([cls1,cls2]):
            return True

    return False

if __name__ == '__main__':
    async def main():
        driver = setup_driver()
        async with driver.bidi_connection() as session:
            Log.info("Selenium CDP session open")
            cdpSession = session.session
            await cdpSession.execute(
                devtools.emulation.set_geolocation_override(**location_override, accuracy=95))
            while actions(driver, session): pass
            s=10
            Log.info("Closing Selenium WebDriver in %s seconds"%s)
            sleep(s)
            driver.quit()

    trio.run(main)
