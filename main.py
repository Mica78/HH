import datetime
import json
import re
import requests
import sys
from bs4 import BeautifulSoup
from fake_headers import Headers
from unicodedata import normalize
from pycbrf.toolbox import ExchangeRates
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def get_start_finish_salary(salary_text):
    salary_match = re.search(
        pattern=r"([0-9]+\s*[0-9]+)+\s*([-–до]+)*\s*([0-9]+\s*[0-9]+)*",
        string=salary_text,
        flags=re.I
    )
    salary_start = str()
    salary_finish = str()
    if salary_match:
        salary_start = normalize('NFKD', salary_match.group(1)).replace(" ", "")
        if salary_match.group(2):
            salary_finish = normalize('NFKD', salary_match.group(3)).replace(" ", "")
        else:
            salary_finish = normalize('NFKD', salary_match.group(1)).replace(" ", "")
    return salary_start, salary_finish


def get_salary_usd(salary_text, date=datetime.date.today()):
    usd_flag = re.search("USD", salary_text, re.I)
    start, finish = get_start_finish_salary(salary_text)
    if start and finish:
        if usd_flag:
            return int(start), int(finish)
        else:
            for r in ExchangeRates(str(date.strftime('%Y-%m-%d'))).rates:
                if r.id == 'R01235':
                    rate = r.value
            return int(int(start) / rate), int(int(finish) / rate)
    else:
        return None, None


def get_vacancy(href):
    req = requests.get(
        url=href,
        headers=Headers(browser="firefox", os="win").generate()
    ).text
    soup = BeautifulSoup(req, features="lxml")
    text = soup.find(attrs={"data-qa": re.compile("vacancy-description")})  # data-qa="vacancy-description"
    if text:
        for t in text:
            if re.search('Django', t.text, re.I) or re.search('Flask', t.text, re.I):
                company_name = soup.find(attrs={"data-qa": re.compile("company-name")})
                try:
                    company_name = company_name.text
                    company_name = normalize('NFKD', company_name)
                except AttributeError:
                    company_name = None
                try:
                    salary_text = soup.find('div', class_='vacancy-title').text
                except AttributeError:
                    salary_text = None

                salary_usd = get_salary_usd(salary_text=salary_text)

                location = soup.find(attrs={"data-qa": re.compile("location")})
                try:
                    location = location.text
                    location = location.split(',')[0]
                except AttributeError:
                    location = None

                return {
                    "link": href,
                    "company name": company_name,
                    "salary start": salary_usd[0],
                    "salary_finish": salary_usd[1],
                    "location": location
                }
    else:
        return {
            "link": href,
            "transcription": "No text"
        }


def append_data(links, result_lst, url):
    for link in links:
        result = get_vacancy(link.get_attribute('href'))
        print(link.get_attribute('href'), result)
        if result:
            result_lst.append(result)


def find_links(driver, res_lst):
    driver.get(url)
    links = driver.find_elements(By.CLASS_NAME, 'serp-item__title')
    append_data(links, res_lst, url)
    new_link = driver.find_elements(By.XPATH, '//*[@data-qa="pager-next"]')
    return new_link


if __name__ == '__main__':
    options = Options()
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_argument('blink-settings=imagesEnabled=false')
    options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    url = 'https://spb.hh.ru/search/vacancy?text=python&area=1&area=2'
    links_list = []

    new_link = find_links(driver, links_list)
    for f in new_link:
        url = f.get_attribute('href')
    while url:
        new_link = find_links(driver, links_list)
        if not new_link:
            break
        for f in new_link:
            url = f.get_attribute('href')

    driver.close()
    print(links_list)

    with open('file.json', "w", encoding="utf-8") as file:
        json.dump(links_list, file, indent=4, ensure_ascii=False)

    sys.exit()
