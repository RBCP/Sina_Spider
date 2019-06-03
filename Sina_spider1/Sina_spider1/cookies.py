# encoding=utf-8
import base64
import requests
import sys
import time
import random
from Sina_spider1.ims import ims
from io import StringIO,BytesIO
from PIL import Image
from math import sqrt
from selenium import webdriver
from selenium.webdriver.remote.command import Command
from selenium.webdriver.common.action_chains import ActionChains
import logging
from Sina_spider1.yumdama import identify
import json
import urllib, urllib.request
from http import cookiejar
from urllib import parse
PIXELS=[]
#reload(sys)
#sys.setdefaultencoding('utf8')
IDENTIFY = 1 # 验证码输入方式:        1:看截图aa.png，手动输入     2:云打码
COOKIE_GETWAY = 0# 0 代表从https://passport.weibo.cn/sso/login 获取cookie   # 1 代表从https://weibo.cn/login/获取Cookie
logger = logging.getLogger(__name__)
logging.getLogger("selenium").setLevel(logging.WARNING)  # 将selenium的日志级别设成WARNING，太烦人


"""
输入你的微博账号和密码，可去小号商场够买。http://www.xiaohao.shop/Home/CatGood/index/cat/5.html
建议买几十个，微博限制的严，太频繁了会出现302转移。
或者你也可以把时间间隔调大点。
"""
myWeiBo = [
   {'no':'','psw':''}
]
def getExactly(im):
    """ 精确剪切"""
    imin = -1
    imax = -1
    jmin = -1
    jmax = -1
    row = im.size[0]
    col = im.size[1]
    for i in range(row):
        for j in range(col):
            if im.load()[i, j] != 255:
                imax = i
                break
        if imax == -1:
            imin = i

    for j in range(col):
        for i in range(row):
            if im.load()[i, j] != 255:
                jmax = j
                break
        if jmax == -1:
            jmin = j
    return (imin + 1, jmin + 1, imax + 1, jmax + 1)
def getType(browser):
    """ 识别图形路径 """
    ttype = ''
    time.sleep(3.5)
    im0 = Image.open(BytesIO(browser.get_screenshot_as_png()))
    box = browser.find_element_by_id('patternCaptchaHolder')
    im = im0.crop((int(box.location['x']) + 10, int(box.location['y']) + 100, int(box.location['x']) + box.size['width'] - 10, int(box.location['y']) + box.size['height'] - 10)).convert('L')
    newBox = getExactly(im)
    im = im.crop(newBox)
    width = im.size[0]
    height = im.size[1]
    for png in ims.keys():
        isGoingOn = True
        for i in range(width):
            for j in range(height):
                if ((im.load()[i, j] >= 245 and ims[png][i][j] < 245) or (im.load()[i, j] < 245 and ims[png][i][j] >= 245)) and abs(ims[png][i][j] - im.load()[i, j]) > 10: # 以245为临界值，大约245为空白，小于245为线条；两个像素之间的差大约10，是为了去除245边界上的误差
                    isGoingOn = False
                    break
            if isGoingOn is False:
                ttype = ''
                break
            else:
                ttype = png
        else:
            break
    px0_x = box.location['x'] + 40 + newBox[0]
    px1_y = box.location['y'] + 130 + newBox[1]
    PIXELS.append((px0_x, px1_y))
    PIXELS.append((px0_x + 100, px1_y))
    PIXELS.append((px0_x, px1_y + 100))
    PIXELS.append((px0_x + 100, px1_y + 100))
    return ttype


def move(browser, coordinate, coordinate0):
    """ 从坐标coordinate0，移动到坐标coordinate """
    time.sleep(0.05)
    length = sqrt((coordinate[0] - coordinate0[0]) ** 2 + (coordinate[1] - coordinate0[1]) ** 2)  # 两点直线距离
    if length < 4:  # 如果两点之间距离小于4px，直接划过去
        ActionChains(browser).move_by_offset(coordinate[0] - coordinate0[0], coordinate[1] - coordinate0[1]).perform()
        return
    else:  # 递归，不断向着终点滑动
        step = random.randint(3, 5)
        x = int(step * (coordinate[0] - coordinate0[0]) / length)  # 按比例
        y = int(step * (coordinate[1] - coordinate0[1]) / length)
        ActionChains(browser).move_by_offset(x, y).perform()
        move(browser, coordinate, (coordinate0[0] + x, coordinate0[1] + y))


def draw(browser, ttype):
    """ 滑动 """
    if len(ttype) == 4:
        px0 = PIXELS[int(ttype[0]) - 1]
        login = browser.find_element_by_id('loginAction')
        ActionChains(browser).move_to_element(login).move_by_offset(px0[0] - login.location['x'] - int(login.size['width'] / 2), px0[1] - login.location['y'] - int(login.size['height'] / 2)).perform()
        browser.execute(Command.MOUSE_DOWN, {})

        px1 = PIXELS[int(ttype[1]) - 1]
        move(browser, (px1[0], px1[1]), px0)

        px2 = PIXELS[int(ttype[2]) - 1]
        move(browser, (px2[0], px2[1]), px1)

        px3 = PIXELS[int(ttype[3]) - 1]
        move(browser, (px3[0], px3[1]), px2)
        browser.execute(Command.MOUSE_UP, {})
    else:
        print ('Sorry! Failed! Maybe you need to update the code.')

def getCookie(account, password):
    print(COOKIE_GETWAY)
    if COOKIE_GETWAY == 0:
        return SinaWeibo_GetCookies(account,password)
    elif COOKIE_GETWAY ==1:
        return get_cookie_from_weibo_cn(account, password)
    else:
        logger.error("COOKIE_GETWAY Error!")


def SinaWeibo_GetCookies( username, password):
    sso_url = "https://passport.weibo.cn/sso/login"
    login_data = urllib.parse.urlencode([
        ('username',username),
        ('password',password),
        ('entry','mweibo'),
        ('client_id', ''),
        ('savestate', '1'),
        ('ec', ''),
    ]).encode(encoding='UTF-8')
    req = urllib.request.Request(sso_url)
    req.add_header('Origin', 'https://passport.weibo.cn')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.14 (KHTML, like Gecko) Chrome/10.0.601.0 Safari/534.14')
    req.add_header('Referer', 'https://passport.weibo.cn/signin/login?entry=mweibo&res=wel&wm=3349&r=http%3A%2F%2Fm.weibo.cn%2F')
    weibo_cookies = cookiejar.CookieJar()
    handler = urllib.request.HTTPCookieProcessor(weibo_cookies)
    opener =urllib.request.build_opener(handler)
    opener.open(req, data=login_data)
    cookie = dict()
    if weibo_cookies._cookies.__contains__(".weibo.cn"):
        logging.info("获取密码成功："+str(username))
        weibo_cn_cookiejar = weibo_cookies._cookies[".weibo.cn"]["/"]
        cookie['SCF'] = weibo_cn_cookiejar['SCF'].value
        cookie['SSOLoginState'] = weibo_cn_cookiejar['SSOLoginState'].value
        cookie['SUB'] = weibo_cn_cookiejar['SUB'].value
        cookie['SUHB'] = weibo_cn_cookiejar['SUHB'].value
    else:
        logger.info("获取账号:"+str(username)+" 的cookie失败，原因：1. 账号或密码错误。 2. 微博登录次数过多，可以换网络登录或过4小时再登录！")
    return cookie


def get_cookie_from_weibo_cn(account, password):
    """ 获取一个账号的Cookie """
    try:
         browser=webdriver.Chrome("E:/Python/chromedriver.exe")
         browser.set_window_size(1050,840)
         browser.get("https://passport.weibo.cn/signin/login?entry=mweibo&r=https://weibo.cn/")
         time.sleep(1)
         name=browser.find_element_by_id('loginName')
         psw=browser.find_element_by_id('loginPassword')
         login=browser.find_element_by_id('loginAction')
         name.send_keys(account)
         psw.send_keys(password)
         login.click()
         ttype=getType(browser)
         print('Result %s' %ttype)
         draw(browser,ttype)
         time.sleep(20)
         cookie={}
         print(type(cookie))
         if "我的首页" in browser.title:
            for elem in browser.get_cookies():
                cookie[elem["name"]] = elem["value"]
            logger.warning("Get Cookie Success!( Account:%s )" % account)
         return cookie
    except Exception:
        logger.warning("Failed %s!" % account)
        return ""
    finally:
        try:
            browser.quit()
        except Exception:
            pass


def getCookies(weibo):
    """ 获取Cookies """
    cookies =[]
    for elem in weibo:
        account = elem['no']
        password = elem['psw']
        cookie  =  getCookie(account, password)
        if cookie!=None and len(cookie.keys())!=0:
            cookies.append(cookie)
    if len(cookie)==0:
        logger.info("没有cookie可以使用，爬虫系统将退出！")
        sys.exit(0)
    return cookies
cookies = getCookies(myWeiBo)
logger.warning("Get Cookies Finish!( Num:%d)" % len(cookies))
