from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_session import Session
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
from apscheduler.schedulers.background import BackgroundScheduler
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
scheduler = BackgroundScheduler()
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


def parse_ticket(raw_str, station_map,from_code, to_code, from_station,to_station,date):
    try:
        decoded_str = unquote(raw_str.replace("%0A", ""))
        fields = decoded_str.split('|')
        return {
            'date' : date,
            'from_city':from_station,
            'to_city':to_station,
            'from_code': from_code,
            'to_code': to_code,
            'car_important_masage1': fields[2],
            'train_number': fields[3],
            'departure_station': station_map.get(fields[6], fields[6]),
            'arrival_station': station_map.get(fields[7], fields[7]),
            'departure_time': fields[8],
            'arrival_time': fields[9],
            'duration': fields[10],
            'car_important_masage2': fields[16],
            'car_important_masage3': fields[17],
            'seats': {
                '二等座': fields[30] or '无',
                '一等座': fields[31] or '无',
                '商务座': fields[32] or '无',
                '硬卧': fields[28] or '无',
                '软卧': fields[23] or '无',
                '无座': fields[26] or '无',
                '硬座': fields[29] or '无',
            }
        }
    except Exception as e:
        print(f"解析错误: {str(e)}")
        return None
    
def get_station_code(name):
    url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9276'
    resp = requests.get(url)
    resp.encoding = 'UTF-8'
    stations = re.findall(r'([\u4e00-\u9fa5]+)\|([A-Z]+)', resp.text)
    return next((code for station, code in stations if station == name), None)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/saoma', methods=['GET', 'POST'])
def saoma():
    global driver
    if driver is None:
        driver = webdriver.Chrome(options=options)
    
    try:
        driver.get('https://kyfw.12306.cn/otn/view/index.html')
        time.sleep(2)  # 等待页面加载完成
        driver.find_element(By.CSS_SELECTOR, ".login-hd-account").click()
        time.sleep(1)
        # 获取图片元素
        img_element = driver.find_element(By.CSS_SELECTOR, '#J-qrImg')
        print('1')
        # 获取图片的src属性（图片的URL）
        img_url = img_element.get_attribute("src")
        
        print(img_url)
        # 等待跳转或显示身份证输入框
        
        return jsonify({'status': 'success', 'message': '请输入身份证后四位', 'img_url':img_url})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/saomalogin', methods=['GET', 'POST'])
def saomalogin():
    data = request.json
    from_city = data['from_city']
    to_city = data['to_city']
    date = data['date']
    car_important_masage1 = data['car_important_masage1']
    car_important_masage2 = data['car_important_masage2']
    car_important_masage3 = data['car_important_masage3']
    passengers = data['passengers']
    booking_time = data['bookingTime']
    seatType = data['seatType']
    try:
        while True:
            try:
                # 尝试查找.class为page-login的元素
                element = driver.find_element(By.CSS_SELECTOR, '.page-login')
                print("检测到page-login类，继续等待...")
                # 设置等待时间，避免过于频繁检测
                import time
                time.sleep(0.5)
            except NoSuchElementException:
                print("page-login类已消失，退出循环。")
                from datetime import datetime
                run_date = datetime.strptime(booking_time, '%Y-%m-%dT%H:%M')
                scheduler.add_job(book_tickets, 'date', run_date=run_date, args=[from_city, to_city, date,car_important_masage1,car_important_masage2,car_important_masage3, passengers, seatType])
                scheduler.start()
                break
        return jsonify({'status': 'success', 'message': '登录成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.json
    username = data['username']
    password = data['password']
    
    global driver
    if driver is None:
        driver = webdriver.Chrome(options=options)
    
    try:
        driver.get('https://kyfw.12306.cn/otn/view/index.html')
        
        # 输入账号和密码
        driver.find_element(By.CSS_SELECTOR, '#J-userName').send_keys(username)
        driver.find_element(By.CSS_SELECTOR, '#J-password').send_keys(password)
        driver.find_element(by="css selector", value="#J-login").click()
        
        # 等待跳转或显示身份证输入框
        time.sleep(2)
        if 'id_card' in driver.page_source:
            return jsonify({'status': 'success', 'message': '请输入身份证后四位'})
        else:
            return jsonify({'status': 'error', 'message': '登录失败，请检查账号密码'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/send_code', methods=['POST'])
def send_verification_code():
    data = request.json
    id_card = data['id_card']
    
    try:
        # 输入身份证后四位
        id_card_element = driver.find_element(By.CSS_SELECTOR, '#id_card')
        id_card_element.clear()
        id_card_element.send_keys(id_card)
        
        # 点击获取验证码按钮
        verification_code_button = driver.find_element(By.CSS_SELECTOR, '#verification_code')
        verification_code_button.click()
        time.sleep(2)
        
        # 获取验证码
        verification_code_element = driver.find_element(By.CSS_SELECTOR, '#code')
        verification_code = verification_code_element.text
        
        return jsonify({'status': 'success', 'verification_code': verification_code})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    id_card = data['id_card']
    verification_code = data['verification_code']
    from_city = data['from_city']
    to_city = data['to_city']
    date = data['date']
    car_important_masage1 = data['car_important_masage1']
    car_important_masage2 = data['car_important_masage2']
    car_important_masage3 = data['car_important_masage3']
    passengers = data['passengers']
    booking_time = data['bookingTime']
    seatType = data['seatType']
    print(seatType)
    try:
        driver.find_element(By.CSS_SELECTOR, '#code').send_keys(verification_code)
        driver.find_element(By.CSS_SELECTOR, '#verification_code').click()
        driver.find_element(By.CSS_SELECTOR, '#sureClick').click()
        driver.implicitly_wait(5)
        from datetime import datetime
        run_date = datetime.strptime(booking_time, '%Y-%m-%dT%H:%M')

    # 安排任务
        scheduler.add_job(book_tickets, 'date', run_date=run_date, args=[from_city, to_city, date,car_important_masage1,car_important_masage2,car_important_masage3, passengers,seatType])
        scheduler.start()
        return jsonify({'status': 'success', 'message': '登录成功'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    
def book_tickets(from_city, to_city, date,car_important_masage1,car_important_masage2,car_important_masage3, passengers,seatType):
    id_value = "ticket_" + car_important_masage1 + "_" + car_important_masage2 + "_" + car_important_masage3
    ticket_pre = id_value + ' > td.no-br'
    print(seatType)
    try:
        driver.find_element(By.CSS_SELECTOR, "#link_for_ticket").click()
            # 11.1 选择出发的城市--点击那个框
        driver.find_element(by="css selector", value="#fromStationText").click()
    # 11.2 选择出发的城市--选择城市
        driver.find_element(by="css selector", value="#fromStationText").send_keys(from_city)
    # 11.3 选择出发的城市--回车确定
        driver.find_element(by="css selector", value="#fromStationText").send_keys(Keys.ENTER)
 
    # 12.1 选择目的的城市--点击那个框
        driver.find_element(by="css selector", value="#toStationText").click()
    # 12.2 选择目的的城市--选择城市
        driver.find_element(by="css selector", value="#toStationText").send_keys(to_city)
    # 12.3 选择目的的城市--回车确定
        driver.find_element(by="css selector", value="#toStationText").send_keys(Keys.ENTER)
 
    # 13.1 选择出发的日期--点击那个框
        driver.find_element(by="css selector", value="#train_date").clear()
    # 12.2 选择出发的日期--选择城市
        driver.find_element(by="css selector", value="#train_date").send_keys(date)
    # 12.3 选择出发的日期--回车确定
        driver.find_element(by="css selector", value="#train_date").send_keys(Keys.ENTER)
    # # 12.4 点击--显示全部可预订的车次
    # driver.find_element(by="css selector", value="avail_ticket").click()
    # 12.5 点击查询
        driver.implicitly_wait(5)
        driver.find_element(by="css selector", value="#query_ticket").click()
        driver.implicitly_wait(5)
        driver.find_element(by="css selector", value=f"#{ticket_pre}").click()
        driver.implicitly_wait(5)
        # for passenger in passengers:
        #     select_passenger = "normalPassenger_" + passenger
        #     driver.find_element(by="css selector", value=f"#{select_passenger}").click()
        # driver.find_element(by="css selector", value="#normalPassenger_0").click()

        for num in passengers:
            if num == '0':
                driver.find_element(by="css selector", value="#normalPassenger_0").click()
                driver.find_element(by="css selector", value='#dialog_xsertcj_cancel').click()
            elif num == '1':
                driver.find_element(by="css selector", value="#normalPassenger_1").click()
            elif num == '2':
                driver.find_element(by="css selector", value="#normalPassenger_2").click()
            elif num == '3':
                driver.find_element(by="css selector", value="#normalPassenger_3").click()
            elif num == '4':
                driver.find_element(by="css selector", value="#normalPassenger_4").click()
            pass
        
 
    # 13.2 提交订单

    # 13.3 选择靠窗的1F的位置
    # driver.find_element(by="css selector", value='#1F').click() --这种行不通，只能下方这种
        if seatType == "二等座":
            driver.find_element(by="css selector", value='#submitOrder_id').click()
            driver.implicitly_wait(5)
            for num in passengers:
                if num == '0':
                    driver.find_element(by="css selector", value='#erdeng1 > ul:nth-child(4) > li:nth-child(2)').click()
                elif num == '1':
                    driver.find_element(by="css selector", value='#erdeng1 > ul:nth-child(4) > li:nth-child(1)').click()
                elif num == '2':
                    driver.find_element(by="css selector", value='#erdeng1 > ul:nth-child(2) > li:nth-child(1)').click()
                elif num == '3':
                    driver.find_element(by="css selector", value='#erdeng1 > ul:nth-child(2) > li:nth-child(2)').click()
                elif num == '4':
                    driver.find_element(by="css selector", value='#erdeng1 > ul:nth-child(2) > li:nth-child(3)').click()
                pass
        
        if seatType == "一等座":
            select_element = driver.find_element("id", "seatType_1")
            select = Select(select_element)
            select.select_by_value('M') # 选择一等座
            driver.find_element(by="css selector", value='#submitOrder_id').click()
            driver.implicitly_wait(5)
            for num in passengers:
                if num == '0':
                    driver.find_element(by="css selector", value='#yideng1 > ul:nth-child(4) > li:nth-child(2)').click()
                elif num == '1':
                    driver.find_element(by="css selector", value='#yideng1 > ul:nth-child(4) > li:nth-child(1)').click()
                elif num == '2':
                    driver.find_element(by="css selector", value='#yideng1 > ul:nth-child(2) > li:nth-child(1)').click()
                elif num == '3':
                    driver.find_element(by="css selector", value='#yideng1 > ul:nth-child(2) > li:nth-child(2)').click()
                pass
        
        if seatType == "商务座":
            select_element = driver.find_element("id", "seatType_1")
            select = Select(select_element)
            select.select_by_value('9') # 选择一等座
            driver.find_element(by="css selector", value='#submitOrder_id').click()
            driver.implicitly_wait(5)

        #火车
        if seatType == "硬卧":
            driver.find_element(by="css selector", value='#submitOrder_id').click()
            driver.implicitly_wait(5)
            for num in passengers:
                if num == '0':
                    driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
                elif num == '1':
                   driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
                elif num == '2':
                    driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
                elif num == '3':
                    driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
                pass
        
        if seatType == "硬座":
            select_element = driver.find_element("id", "seatType_1")
            select = Select(select_element)
            select.select_by_value('1')
            driver.find_element(by="css selector", value='#submitOrder_id').click()
            driver.implicitly_wait(5)

        if seatType == "软卧":
            select_element = driver.find_element("id", "seatType_1")
            select = Select(select_element)
            select.select_by_value('4') 
            driver.find_element(by="css selector", value='#submitOrder_id').click()
            driver.implicitly_wait(5)
            # for num in passengers:
            #     if num == '0':
            #         driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
            #     elif num == '1':
            #        driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
            #     elif num == '2':
            #         driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
            #     elif num == '3':
            #         driver.find_element(by="css selector", value='#id-bed-sel > div:nth-child(2) > div:nth-child(1) > div:nth-child(1)>div:nth-child(2) > a:nth-child(3)').click()
            #     pass

        while True:
            try:
                # 尝试查找.class为page-login的元素
                element = driver.find_element(By.CSS_SELECTOR, '#id-bed-sel')
                # driver.find_element(by="css selector", value='#qr_submit_id').click()
                # print('1')
                driver.implicitly_wait(5)
            except NoSuchElementException:
                break
    # 13.4 再次确认提交
        # time.sleep(2)
        # driver.find_element(by="css selector", value='#qr_submit_id').click()
        pass

    except Exception as e:
        pass
@app.route('/query', methods=['POST'])
def query_tickets():
    data = request.json
    from_station = data['from']
    to_station = data['to']
    date = data['date']

    try:
        query_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')
    except ValueError:
        return jsonify({"error": "日期格式错误"}), 400

    from_code = get_station_code(from_station)
    to_code = get_station_code(to_station)

    if not from_code or not to_code:
        return jsonify({"error": "车站名称错误"}), 400

    params = {
        "leftTicketDTO.train_date": date,
        "leftTicketDTO.from_station": from_code,
        "leftTicketDTO.to_station": to_code,
        "purpose_codes": "ADULT"
    }

    api_url = 'https://kyfw.12306.cn/otn/leftTicket/queryG'
    try:
        resp = session.get(api_url, params=params)
        resp.raise_for_status()
        data = resp.json()
  
        if data.get('httpstatus') == 200 and 'data' in data:
            station_map = data['data'].get('map', {})
            tickets = [
                parse_ticket(item, station_map,from_code, to_code,from_station,to_station,date)
                for item in data['data']['result']
                if parse_ticket(item, station_map,from_code, to_code,from_station,to_station,date) is not None
            ]
            return jsonify(tickets)
        return jsonify({"error": "未找到车次信息"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        time.sleep(1)

@app.route('/book', methods=['GET', 'POST'])
def handle_booking():
    if request.method == 'GET':
        train_data = request.args.get('data')
        if not train_data:
            return redirect(url_for('index'))
        return render_template('book.html')

    # POST处理
    try:
        data = request.json
        required_fields = ['train_number', 'seat_type', 'passengers']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
  
        print(f"模拟抢票：{data['train_number']} {data['seat_type']} {data['passengers']}")
        time.sleep(1)
  
        if random.random() < 0.8:
            return jsonify({
                "success": True,
                "order_id": f"B2025{random.randint(1000,9999)}",
                "train_info": data['train_number'],
                "seat_type": data['seat_type'],
                "passengers": data['passengers']
            })
        else:
            return jsonify({"success": False, "error": "余票不足"})
      
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
