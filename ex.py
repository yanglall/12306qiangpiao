
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import random
from urllib.parse import unquote
from selenium.webdriver.common.keys import Keys

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
    "Cookie": "_uab_collina=174020812724582227549917; JSESSIONID=E9373920FF438544E2C143BE905E3F05; tk=j9YfBLPgJqJFIqzOPamrbxrQq4iB3AK3m3HA5m9PKTwmkh1h0; BIGipServerotn=1557725450.50210.0000; BIGipServerpassport=954728714.50215.0000; guidesStatus=off; highContrastMode=defaltMode; cursorStatus=off; BIGipServerportal=3151233290.17695.0000; route=9036359bb8a8a461c164a04f8f50b252; uKey=e8379fb1bd24ce60becc8a401bb0c45537936cd79c75ef61a4e44a250edc7235; _jc_save_fromStation=%u6210%u90FD%2CCDW; _jc_save_toStation=%u5317%u4EAC%2CBJP; _jc_save_fromDate=2025-02-22; _jc_save_toDate=2025-02-22; _jc_save_wfdc_flag=dc"
})

# 配置Selenium
user_data_dir = os.path.join(os.getcwd(), 'selenium_data')
options = Options()
options.add_argument(f'--user-data-dir={user_data_dir}')
driver = None


if driver is None:
    driver = webdriver.Chrome(options=options)

    driver.get('https://kyfw.12306.cn/otn/view/index.html')
