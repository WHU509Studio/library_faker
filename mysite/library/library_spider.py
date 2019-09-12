# from login import LibraryLogin
import requests
import fake_useragent
import json
import os
import aiohttp
from contextvars import ContextVar
import asyncio
from pyquery import PyQuery as pq
from threading import Thread
import time
from datetime import datetime
from copy import deepcopy
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JSON_PATH = os.path.join(BASE_DIR, "library_urls.json")

concurrent = ContextVar("concurrent")

def parse_json(data_json):
    with open("room.txt", "w", encoding="utf8") as f:
        f.write(data_json)

def get_json_humanly(url, ua, cookies, onDate="", building="null", room="null",
                    hour="null", startMin="null", endMin="null",
                    power="null", window="null"):
    headers = {
        "User-Agent": ua,
        "Host": "seat.lib.whu.edu.cn",
        "Referer": "https://seat.lib.whu.edu.cn/",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    # 注意这里必须要使用 application/x-www-form-urlencoded 编码格式
    payload = {
        "onDate": onDate,
        "building": building,
        "room": room,
        "hour": hour,
        "startMin": startMin,
        "endMin": endMin,
        "power": power,
        "window": window
    }
    print(payload)
    r = requests.post(url=url, headers=headers, data=payload, cookies=cookies)
    if r.status_code == 200:
        return r.json()
    else:
        print(r.status_code)
        print(r.text)

async def get_json(url, ua, cookies, onDate="", building="null", room="null",
                    hour="null", startMin="null", endMin="null",
                    power="null", window="null"):

    headers = {
        "User-Agent": ua,
        "Host": "seat.lib.whu.edu.cn",
        "Referer": "https://seat.lib.whu.edu.cn/",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    # 注意这里必须要使用 application/x-www-form-urlencoded 编码格式
    payload = {
        "onDate": onDate,
        "building": building,
        "room": room,
        "hour": hour,
        "startMin": startMin,
        "endMin": endMin,
        "power": power,
        "window": window
    }
    print(payload)
    sem = concurrent.get()
    try:
        async with sem:
            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, headers=headers, 
                                        data=payload, cookies=cookies) as resp:
                    data_json = await resp.text()
                    parse_json(data_json)
    except Exception as e:
        print(e.args)
                    

# 检查 cookie 是否合法
def check_valid_cookie(cookies):
    url = "https://seat.lib.whu.edu.cn/"
    headers = {
        "User-Agent": fake_useragent.UserAgent().random,
        "Host": "seat.lib.whu.edu.cn",
        "Referer": "https://seat.lib.whu.edu.cn/",
    }
    r = requests.get(url=url, headers=headers, cookies=cookies)
    if r.status_code == 200:
        if r.url == url:
            if r.text == "系统维护中，请稍候访问":
                return 2
            return True

    return False

class LibrarySpider:

    def __init__(self, name=None, pwd=None, cookies=None):
        if not (name or pwd or cookies):
            raise Exception("name and pwd or cookies needed!")
        if not cookies:
            self.name = name
            self.pwd = pwd
            # 必须配合登陆脚本才能使用
            # self._get_cookie()
            raise Exception("cookies needed！")
        else:
            self.cookies = cookies
        
        self.ua = fake_useragent.UserAgent()
        self.base_headers = {
            "Host": "seat.lib.whu.edu.cn",
            "Referer": "http://seat.lib.whu.edu.cn/",
            "Origin": "https://seat.lib.whu.edu.cn"
        }
        self._load_data()

        # 图书馆使用 session 而非 cookie，只要客户端一直活动，那么session就永远不会过期
        Thread(target=self._update_cookies).start()
        # 返回是否抢座，若抢座返回抢座的信息
        self._get_seat_info()



    # 随机更换ua
    def _add_random_ua(self):
        headers = deepcopy(self.base_headers)
        headers["User-Agent"] = self.ua.random
        return headers

    # 为了避免 sessionid 过期，定时更新
    def _update_cookies(self):
        url = "http://seat.lib.whu.edu.cn/"

        headers = self._add_random_ua()
        
        while True:
            r = requests.get(url=url, headers=headers, cookies=self.cookies)
            if r.url == url:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  维持会话成功")
                time.sleep(600)
            else:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  建立连接失败")
                # 强制退出，终止 python 解释器
                os._exit(-1)




    def _get_seat_info(self):
        
        url = "https://seat.lib.whu.edu.cn/history?"

        headers = self._add_random_ua()

        params = {
            "type": "SEAT"
        }
        r = requests.get(url=url, headers=headers, params=params, cookies=self.cookies)
        if r.status_code == 200:
            doc = pq(r.text)
            # 这里不是很好写
            content = doc(".myReserveList dl:first-child a")
            seat_info = {}
            seat_info["location_info"] = content[0].text.strip()
                # 此时情况是已经预约但是没有签到
            if len(content) == 3:
                cancel_url = content[1].attrib.get("href")
                seat_info["cancel_url"] = "https://seat.lib.whu.edu.cn" + cancel_url
                seat_info["state"] = content[2].text
                # 判断是否能够取消预约
                seat_info["cancel_id"] = True
            # 使用中或者已经完成
            if len(content) == 2:
                seat_info["state"] = content[1].text
                seat_info["cancel_id"] = False
            self.seat_info = seat_info

        else:
            print("获取位置信息失败")
            self.seat_info = {}
            


    def _load_data(self, json_path=JSON_PATH):
        with open(json_path, "r", encoding="utf8") as f:
            ajaxSearch = json.loads(f.read()).get("ajaxSearch")
        self.search_url = ajaxSearch.get("url")
        self.serach_method = ajaxSearch.get("method")
        datas = ajaxSearch.get("datas")
        # 日期需要修改
        self.onDate = datas.get("onDate")
        # 选择场馆 
        self.building = datas.get("building")
        # 选择房间
        self.rooms = datas.get("rooms")
        # 选择时间
        self.hour = datas.get("hour")
        # 选择开始时间
        self.startMin = datas.get("startMin")
        # 选择结束时间
        self.endMin = datas.get("endMin")
        # 选择电源
        self.power = datas.get("power")
        # 选择靠窗
        self.window = datas.get("window")

    # 这里必须配合登陆才能使用
    # def _get_cookie(self):
    #     self.cookies = LibraryLogin(name=self.name, pwd=self.pwd, timeout=10).login()
    
    # 派发请求
    # 采用协程可能会导致封号
    async def send_req(self, building, startMin, endMin, power="null", window="null", onDate=""):
        # 先做一个测试

        # 绑定开始时间和结束时间
        self.startTime = self.startMin.get(startMin)
        self.endTime = self.endMin.get(endMin)

        concurrent.set(asyncio.Semaphore(10))

        tasks = []
        for room in self.rooms.get(building):
            tasks.append(asyncio.create_task(get_json(self.search_url, self.ua.random, cookies=self.cookies, room=room, building=building,
                                                        startMin=self.startTime, endMin=self.endTime)))
        await asyncio.wait(tasks, return_when="ALL_COMPLETED")


    def send_req_humanly(self, building, startMin, endMin, power="null", window="null", onDate=""):
        # 绑定开始时间和结束时间
        self.startTime = self.startMin.get(startMin)
        self.endTime = self.endMin.get(endMin)
        # 随机抢座
        pattern = re.compile(".*?(\d+)")
        flag = 0
        for room, room_id in self.rooms.get(building).items():
            if flag:
                break
            time.sleep(1)
            data_json = get_json_humanly(self.search_url, self.ua.random, cookies=self.cookies, room=room_id, building=building,
                                startMin=self.startTime, endMin=self.endTime)
            print(f"正在尝试房间：{room}")
            if data_json.get("seatNum"):
                doc = pq(data_json.get("seatStr"))
                for li in doc("li"):
                    seat_id = pattern.match(li.attrib.get("id")).group(1)
                    print(seat_id)
                    result = self.fetch_seat(seat_id, self.startTime, self.endTime, date="")
                    if result:
                        flag = 1
                        self._get_seat_info()
                        break
        print(f"预约成功，座位信息\n{self.seat_info}")


    def fetch_seat(self, seat_id, startTime, endTime, date=""):
        # 为了获取 token
        
        url = "http://seat.lib.whu.edu.cn/"
        
        headers = self._add_random_ua()

        req = requests.Session()
        r = req.get(url=url, headers=headers, cookies=self.cookies)
        if r.status_code == 200:
            doc = pq(r.text)
            SYNCHRONIZER_TOKEN = doc("#SYNCHRONIZER_TOKEN").attr("value")
            SYNCHRONIZER_URI = doc("#SYNCHRONIZER_URI").attr("value")
        else:
            print("抓取token失败")
            return None

        payload = {
            "SYNCHRONIZER_TOKEN": SYNCHRONIZER_TOKEN,
            "SYNCHRONIZER_URI": SYNCHRONIZER_URI,
            "date": date,
            "seat": seat_id,
            "start": startTime,
            "end": endTime,
            "authid": "-1"
        }
        fetch_url = "https://seat.lib.whu.edu.cn/selfRes"
        res = req.post(url=fetch_url, headers=headers, data=payload, cookies=self.cookies)
        if res.status_code == 200:
            # print(res.text)
            return True
        else:
            print(res.status_code)
            print(res.text)
            return False

    def cancel_seat(self):
        if not self.seat_info.get("cancel_id"):
            print("没有预约或正在使用，无法取消")
            return 
        # 这里需要和 seat_info 配合使用
        url = self.seat_info.get("cancel_url")

        headers = self._add_random_ua()

        r = requests.get(url=url, headers=headers, cookies=self.cookies)
        if r.status_code == 200:
            print("取消预约成功")
            self._get_seat_info()
            print(self.seat_info)
        else:
            print(r.status_code)
            print(r.text)

    





if __name__ == "__main__":
    # spider = LibrarySpider("********", "*******")
    # spider = LibrarySpider(cookies={'JSESSIONID': '***************'})
    # print(spider.seat_info)
    # spider.cancel_seat()
    pass