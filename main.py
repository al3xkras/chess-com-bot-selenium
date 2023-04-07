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
    def info(o):
        print(o)

    @staticmethod
    def error(o):
        print(o)


def setup_driver():

    options = Options()
    headless=False
    profile_dir=""

    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-web-security")
    options.add_argument("--mute-audio")
    options.set_capability("acceptInsecureCerts",True)
    options.add_experimental_option("excludeSwitches",["enable-automation"])
    options.add_experimental_option("useAutomationExtension",False)

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    #options.addExtensions(new File("./adblock.crx"));
    options.add_argument("--disable-popup-blocking")
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
    url = "https://www.chess.com/"

    piece_types = { "p", "b", "n", "r", "k", "q"}
    piece_colors={ "w", "b" }
    piece_classes = set(y+x for x in piece_types for y in piece_colors)

    board_items = [[(i,j) for i in range(1,9)] for j in range(8,0,-1)]

    def get_position(driver:webdriver.Chrome, wait:WebDriverWait):
        pieces_ = driver.find_elements(By.CLASS_NAME,"piece")
        pieces=[]
        for piece in pieces_:
            classes = piece.get_attribute("class").split()
            p = Piece(None,None)
            for cls in classes:
                if cls.startswith("square-"):
                    pos = cls.lstrip("square-")
                    p.pos=int(pos[0]),int(pos[1])
                elif cls in piece_classes:
                    p.type=cls
            if p.type is None or p.pos is None:
                Log.error("piece init failed: %s"%p)

    def actions(driver:webdriver.Chrome,session):
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 15)
            element = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "board"))
            )

            element = wait.until(
                EC.presence_of_element_located((By.ID, "board"))
            )

        except:
            pass

    async def main():
        driver = setup_driver()
        async with driver.bidi_connection() as session:
            Log.info("session open")
            cdpSession = session.session
            await cdpSession.execute(
                devtools.emulation.set_geolocation_override(latitude=48.8781, longitude=-28.6298, accuracy=95))
            actions(driver,session)
            driver.quit()


    #trio.run(main)
    for x in board_items:
        print(x)