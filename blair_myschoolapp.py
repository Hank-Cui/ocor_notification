# Foundations
import os
import time 
from datetime import datetime
from datetime import timedelta
import pytz
import numpy as np

# 爬虫
from selenium import webdriver

from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 发短信的

import twilio
from twilio.rest import Client

# 数据库
import database_ocor as ocordb

account_sid = os.environ.get("twilio_account_sid")
auth_token = os.environ.get("twilio_auth_token")

client = Client(account_sid, auth_token)
# wd = webdriver.Chrome('/Users/imf/Desktop/schoolapp/chromedriver')
wd = webdriver.Chrome('chromedriver')

# 发送信息
def send_message(message_body, phone_number):
    message = client.messages \
        .create(
            body=str(message_body),
            from_='+17343999338',
            to=phone_number
        )
    print(message.sid)


# 找到每个Block的开始时间
def get_start_time(block, date):
    L = np.array([])
    for time in block[:, 0]:
        a = time.find(" ")
        if a == 4:
            L = np.append(L, datetime.strptime\
                (date+time[a-4:a+3], '%Y-%m-%d %I:%M %p'))
        elif a == 5:
            L = np.append(L, datetime.strptime\
                (date+time[a-5:a+3], '%Y-%m-%d %I:%M %p'))
    block = np.insert(block, 0, L, axis=1)
    return block



def time_diff(time, min_diff):  # Pass a string to it
    timezone = pytz.timezone('America/New_York')
    now = datetime.now(tz=timezone).replace(tzinfo=None)
    return datetime.strptime(time, '%Y-%m-%d %H:%M:%S')\
        - timedelta(minutes=min_diff) < now


def restart_wd():
    global wd
    try:
        wd.close()
        wd.quit()
        wd = webdriver.Chrome('chromedriver')
    except:
        wd = webdriver.Chrome('chromedriver')


# Schoolapp网页爬虫，return 网页的 html


def get_schedule_and_date(s_username, s_password):
    global date_today
    restart_wd()

    wd.get("https://blair.myschoolapp.com/app/#login")                              # Get on the website with webdriver
    wait = WebDriverWait(wd, 10)                                                    # Set wait class
    user_input = wait.until(EC.presence_of_element_located((By.ID, 'Username')))    # 等到登录框加载出来
    user_input.send_keys(s_username)                                                # 输入用户名
    nbt = wait.until(EC.presence_of_element_located((By.ID, 'nextBtn')))            # 等待Nest按钮加载出来
    nbt.click()                                                                     # 点击next按钮
    pw_input = wait.until(EC.visibility_of_element_located((By.ID, 'Password')))    # 等待加载出来
    pw_input.send_keys(s_password)                                                  # 输入密码
    wait.until(EC.visibility_of_element_located((By.ID, 'loginBtn')))               # 等待登录按钮加载出来 
    wd.find_element_by_id('loginBtn').click()                                       # 点击登录按钮
    date_exist = False

    # Sometimes the date doesn't load, so refresh the page.
    while not date_exist:
        try:
            path = '//*[@id="schedule-header"]/div/div/div/div[2]/div[1]/h2'
            date_today = wait.until(EC.presence_of_element_located\
                ((By.XPATH, path)))
            date_exist = True
        except:
            wd.refresh()
    wait.until(EC.presence_of_element_located((By.ID, 'accordionSchedules')))       # 等待课程表加载出来
    date_today = datetime.strptime(date_today.text, "%A, %B %d, %Y")

    # 用美丽的汤找到课表
    soup = BeautifulSoup(wd.page_source, 'html.parser')  # 用bs4读html
    table = soup.table
    table_rows = table.find_all('tr')
    blocks = []
    for tr in table_rows:  # 把table存成list
        td = tr.find_all('td')
        row = [i.text.strip() for i in td]
        blocks.append(row)
    schedule = np.array(blocks[1:])
    wd.close()
    wd.quit()
    return schedule, str(date_today)[:11]


def update_schedule_all():
    for name in ocordb.get_roaster():
        username, password = ocordb.get_username_password(name)
        # 获取课表数据并加上开始时间
        schedule, date = get_schedule_and_date(username, password)
        schedule = get_start_time(schedule, date)

        # 更新数据库中的课表以及日期
        ocordb.update_schedule_and_date(name, date, schedule.tostring())

        wd.quit()
 
# ocordb.create_user('cuih', 'cuih', 'password0', 'student')
update_schedule_all()

while True:
    for name in ocordb.get_roaster():
        blocks = np.frombuffer(ocordb.get_schedule(name)[0], dtype="<U44")
        blocks = blocks.reshape(-1,7)
        phone_number = ocordb.get_phone(name)

        if time_diff(blocks[0][0], 0) == True:

            block_, class_, classtime_ = (
                blocks[0][2], 
                blocks[0][3], 
                blocks[0][1]
            )

            message_body = "Your {} block class {} just started. \
                Class time: {}.".format(block_, class_, classtime_)

            send_message(message_body, phone_number)
            ocordb.update_schedule(name, blocks[1:].tostring())

        elif time_diff(blocks[0][0], 5) == True:

            block_, class_, teacher_, location_ = (
                blocks[0][2], 
                blocks[0][3], 
                blocks[0][4], 
                blocks[0][5]
            )

            message_body = "You have block {}, {}, with {} at {} in {} minutes"\
                .format(block_, class_, teacher_, location_, 5)

            send_message(message_body, phone_number)
            
        elif time_diff(blocks[0][0], 10) == True:

            block_, class_, teacher_, location_ = (
                blocks[0][2], 
                blocks[0][3], 
                blocks[0][4], 
                blocks[0][5]
            )

            message_body = "You have block {}, {}, with {} at {} in {} minutes"\
                .format(block_, class_, teacher_, location_,10)

            send_message(message_body, phone_number)