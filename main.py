import os
import traceback

import selenium
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from time import time,sleep
import selenium.webdriver.common.devtools.v106 as devtools
import trio

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import stockfish


class Log:
    @staticmethod
    def info(*o):
        print(*o)

    @staticmethod
    def error(o):
        print(o)


def setup_driver(profile_path=None):

    options = Options()
    headless=False
    profile_dir=os.getcwd()+"/Profile/Selenium"

    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-web-security")
    options.add_argument("--mute-audio")
    #options.set_capability("acceptInsecureCerts",True)
    options.add_experimental_option("excludeSwitches",["enable-automation"])
    options.add_experimental_option("useAutomationExtension",False)

    options.add_argument("--disable-blink-features=AutomationControlled")
    #options.add_argument("--start-maximized")
    #options.addExtensions(new File("./adblock.crx"));
    #options.add_argument("--disable-popup-blocking")
    if headless:
        options.add_argument("--headless")

    if profile_dir:
        options.add_argument("--user-data-dir="+profile_dir)
        options.add_argument("--profile-directory=Default")

    chrome_driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)

    chrome_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    chrome_driver.execute_cdp_cmd("Network.setUserAgentOverride",{
        "userAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36"
    })

    Log.info(chrome_driver.execute_script("return navigator.userAgent;"))

    return chrome_driver

class Piece:
    def __init__(self,type_:str|None,pos:tuple|None):
        self.type=type_
        self.pos=pos

if __name__ == '__main__':

    # Define the URL of the webpage you want to open
    url = "https://www.chess.com/play/computer"
    #url = "https://nowsecure.nl/"

    num_to_let = dict(zip(range(1,9),"abcdefgh"))
    let_to_num = dict(zip("abcdefgh",range(1,9)))

    def get_last_move(driver:webdriver.Chrome):

        pieces_ = driver.find_elements(By.CLASS_NAME,"piece")
        Log.info("pieces: ", pieces_)
        highlighted = driver.find_elements(By.CLASS_NAME,"highlight")
        Log.info("highlighted: ",highlighted)

        if len(highlighted)<2:
            Log.error("len(highlighted)<2")
            return None
        if len(highlighted)>2:
            Log.error("len(highlighted)>2")

        first,second = highlighted
        for piece in pieces_:
            for cls in piece.get_attribute("class").split():
                if cls.startswith("square-") and cls in first.get_attribute("class"):
                    first,second=second,first
                    break
                elif cls.startswith("square-") and cls in second.get_attribute("class"):
                    break

        f = lambda x : num_to_let[int(x[0])]+x[1]

        tile1 = [f(x.lstrip("square-")) for x in first.get_attribute("class").split() if x.startswith("square-")][0]
        tile2 = [f(x.lstrip("square-")) for x in second.get_attribute("class").split() if x.startswith("square-")][0]
        #piece_type = [x for x in first.get_attribute("class").split() if len(x)==2][0]
        #move_by,piece_type=piece_type[0],piece_type[1]
        return tile1,tile2



    def play(driver:webdriver.Chrome,wait:WebDriverWait,engine:stockfish.Stockfish,move):
        engine.make_moves_from_current_position([move])

        pos0 = move[:2]
        pos1 = move[2:]
        pos0 = "square-"+str(let_to_num[pos0[0]])+pos0[1]
        pos1 = "square-"+str(let_to_num[pos1[0]])+pos1[1]

        cls = " ".join(["piece",pos1,"wp","p1234"])

        Log.info("adding board item")
        scr = """
        var board = document.getElementsByClassName('board').item(0);
        var piece = document.createElement('div');
        
        piece.setAttribute('class', '%s');
        board.appendChild(piece);
        """%cls
        driver.execute_script(scr)
        Log.info("board item added")

        Log.info("making a move...")
        #sleep(1)
        e0 = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, pos0)))
        e0.click()
        Log.info("first clicked...")
        #sleep(0.1)
        e1=wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "p1234")))
        e1.click()
        Log.info("second clicked...")
        #sleep(1)
        Log.info("move is made")
        Log.info("removing the piece...")
        scr1 = """
        var board = document.getElementsByClassName('board').item(0);
        var to_rm = document.getElementsByClassName('p1234').item(0);
        board.removeChild(to_rm)
        """
        driver.execute_script(scr1)
        Log.info("waiting...")
        #sleep()
        Log.info("next move")



    def actions(driver:webdriver.Chrome,session):
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 120)
            Log.info("Waiting for board...")
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "board"))
            )
            Log.info("board found")
            sleep(3)
            board = driver.find_elements(By.CLASS_NAME,"board")[0]

            is_black = "flipped" in board.get_attribute("outerHTML")
            #Log.info("contents: ",board.get_attribute("outerHTML"))
            Log.info("is black: %s"%is_black)

            engine = stockfish.Stockfish(path="C:\stockfish\stockfish-windows-2022-x86-64-avx2.exe")
            engine.set_fen_position(
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", True
            )

            if is_black:
                Log.info("waiting for \"highlight\" element")
                wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME,"highlight"))
                )
                Log.info("element found")
                t1,t2=get_last_move(driver)
                Log.info("last move:",t1+t2)
                engine.make_moves_from_current_position([t1+t2])
            else:
                play(driver,wait,engine,engine.get_best_move())
                wait.until(
                    EC.element_selection_state_to_be((By.CLASS_NAME, "highlight"))
                )
                t1, t2 = get_last_move(driver)
            last_moved=t1
            hl_cls = "square-"+t1
            loops_count_max=100
            loop=0
            while loop<loops_count_max:
                loop+=1
                move=engine.get_best_move()
                Log.info("playing next move: ",move)
                play(driver, wait, engine, move)
                last_moved=str(let_to_num[move[0]])+move[1]

                cls = "square-" + last_moved

                piece = driver.find_element(By.CLASS_NAME,cls)
                state = piece.get_attribute("outerHTML")
                Log.info("move played")
                Log.info("waiting for opponent's move")
                sleep(0.1)

                wait.until(lambda drv: drv.find_element(By.CLASS_NAME,cls).get_attribute("outerHTML")!=state)

                t1, t2 = get_last_move(driver)
                last_moved=t2
                Log.info("opponent's move: ",t1+t2)
                engine.make_moves_from_current_position([t1 + t2])

        except:
            exc=traceback.format_exc()
            print(exc)

    async def main():
        driver = setup_driver()
        async with driver.bidi_connection() as session:
            Log.info("session open")
            cdpSession = session.session
            await cdpSession.execute(
                devtools.emulation.set_geolocation_override(latitude=48.8781, longitude=-28.6298, accuracy=95))
            actions(driver,session)
            sleep(1000)
            driver.quit()

    trio.run(main)