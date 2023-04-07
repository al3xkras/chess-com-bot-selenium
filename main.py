import selenium
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from time import time,sleep
import selenium.webdriver.common.devtools.v106 as devtools
import trio

class Log:
    @staticmethod
    def info(o):
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


if __name__ == '__main__':
    async def main():
        driver = setup_driver()

        async with driver.bidi_connection() as session:
            Log.info("a")
            cdpSession = session.session
            await cdpSession.execute(
                devtools.emulation.set_geolocation_override(latitude=41.8781, longitude=-87.6298, accuracy=95))

            driver.get("https://www.python.org")
            sleep(5)
            driver.quit()

    trio.run(main)
