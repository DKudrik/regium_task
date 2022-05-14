import logging
import sqlite3
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests
from art import tprint
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from sqlalchemy import delete
from sqlalchemy.orm.session import Session
from webdriver_manager.chrome import ChromeDriverManager

from db_utils import Advertisement, create_db
from utils import create_xls

logging.basicConfig(
    level=logging.WARNING,
    filename="program.log",
    format="%(asctime)s, %(levelname)s, %(message)s, %(name)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
handler = RotatingFileHandler("my_logger.log", maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

URL = "https://www.avito.ru/rossiya/avtomobili/jeep/cherokee/iii_restayling-ASgBAgICA0Tgtg3EmCjitg3AoSjqtg2K1Cg?cd=1"


def get_html(url: str) -> str:
    """
    Gets html from the URL and returns it as a string.
    :param url: page url
    :return: page text
    """
    sess = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 502, 503, 504])
    sess.mount("http://", HTTPAdapter(max_retries=retries))
    response = sess.get(url)
    return response.text


def get_current_eur_rub_rate() -> float:
    """
    Returns current rate of eur/rub exchange from the site or Russian Central
    Bank.
    :return: current eur/rub rate of exchange
    """
    url = "http://www.cbr.ru/scripts/XML_daily.asp?"
    try:
        html = get_html(url)
        soup = BeautifulSoup(html, features="xml")
        currencies = soup.find_all("Valute")
        eur_rub_rate = float(currencies[11].find("Value").text.replace(",", "."))
    except Exception as error:
        logging.error(error)
    else:
        return eur_rub_rate


def create_web_driver() -> WebDriver:
    """
    Creates selenium webdriver for processing web pages.
    :return: WebDriver object
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver


def check_if_market_price(advt: WebElement) -> bool:
    """
    Checks if there is a badge 'Market Price'. Returns 'True' if
    there is a badge, otherwise returns 'False'

    :param advt: WebElement with info about price
    :return: bool, depends on a price
    """
    try:
        advt.find_element(By.XPATH, ".//*[ text() = 'Рыночная цена']")
    except NoSuchElementException as error:
        logging.error(error)
        return False
    else:
        return True


def check_if_only_on_avito(advt: WebElement) -> bool:
    """
    Checks if there is a badge 'Only on Avito'. Returns 'True' if
    there is a badge, otherwise returns 'False'

    :param advt: WebElement with info about advt placement
    :return: bool, depends on a placement
    """
    try:
        advt.find_element(By.XPATH, ".//*[ text() = 'Только на Авито']")
    except NoSuchElementException as error:
        logging.error(error)
        return False
    else:
        return True


def check_if_owner(advt: WebElement) -> bool:
    """
    Checks if there is a badge 'Owner'. Returns 'True' if
    there is a badge, otherwise returns 'False'

    :param advt: WebElement with info about ownership
    :return: bool, depends on ownership
    """
    try:
        advt.find_element(By.XPATH, ".//*[ text() = 'Собственник']")
    except NoSuchElementException as error:
        logging.error(error)
        return False
    else:
        return True


def check_if_damaged(advt: WebElement) -> bool:
    """
    Checks if there is a badge 'Damaged'. Returns 'True' if
    there is a badge, otherwise returns 'False'

    :param advt: WebElement with info about damage
    :return: bool, depends on a car condition
    """
    try:
        advt.find_element(By.XPATH, ".//*[ text() = 'Битый']")
    except NoSuchElementException as error:
        logging.error(error)
        return False
    else:
        return True


def get_and_convert_date(advt: WebElement) -> str:
    """Get the date the advt was published/updated and returns it
    as a str with"""
    date_from_advt = advt.find_element(By.XPATH, ".//*[@data-marker='item-date']").text
    final_date = date_from_advt + " от " + datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return final_date


def process_main_page(driver: WebDriver, session: Session) -> None:
    """Processes the main page to get all the data and adds it to the DB"""
    session = session
    driver.get(URL)
    advts = driver.find_elements(By.CLASS_NAME, "iva-item-root-_lk9K")
    advts_to_db = []
    for advt in advts:
        advt_data = []
        advt_id = advt.get_attribute("data-item-id")
        price = int(
            advt.find_element(By.XPATH, ".//*[@itemprop='price']").get_attribute(
                "content"
            )
        )
        price_eur = price / get_current_eur_rub_rate()
        year = int(
            advt.find_element(
                By.XPATH, ".//*[@class='iva-item-titleStep-pdebR']"
            ).text.split(",")[1]
        )
        characteristics = advt.find_element(
            By.XPATH, ".//*[@data-marker='item-specific-params']"
        ).text.split(", ")
        if characteristics[0] == "Битый":
            characteristics.pop(0)
        mileage = characteristics[0]
        engine_volume = characteristics[1].split()[0]
        transmission = characteristics[1].split()[1]
        horse_power = characteristics[1].split()[2].replace("(", "").replace(")", "")
        drive_wheels = characteristics[3]
        fuel = characteristics[4]
        is_market_price = check_if_market_price(advt)
        is_only_on_avito = check_if_only_on_avito(advt)
        is_owner = check_if_owner(advt)
        is_damaged = check_if_damaged(advt)
        description = advt.find_element(
            By.CLASS_NAME, "iva-item-description-FDgK4"
        ).text
        place_of_sale = advt.find_element(
            By.XPATH, ".//span[contains(@class, 'geo-address-fhHd0')]"
        ).text
        url_to_advt_page = advt.find_element(
            By.XPATH, ".//*[@data-marker='item-title']"
        ).get_attribute("href")
        created = get_and_convert_date(advt)
        advt_data.extend(
            (
                advt_id,
                price,
                price_eur,
                year,
                mileage,
                engine_volume,
                transmission,
                horse_power,
                drive_wheels,
                fuel,
                is_market_price,
                is_only_on_avito,
                is_owner,
                is_damaged,
                description,
                place_of_sale,
                url_to_advt_page,
                created,
            )
        )
        if session.query(Advertisement).filter(advt_id == advt_id):
            session.query(Advertisement).filter(
                Advertisement.advt_id == advt_id
            ).delete()
        advts_to_db.append(Advertisement(*advt_data))
    session.bulk_save_objects(advts_to_db)


if __name__ == "__main__":
    tprint("AVITO      PARSER")
    print("[+] Parsing the page...")
    driver = create_web_driver()
    session = create_db()
    process_main_page(driver, session)
    create_xls(session)
    session.commit()
    session.close()
    driver.close()
    driver.quit()
