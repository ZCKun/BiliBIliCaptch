import re

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

from config import *
from PIL import Image
import time
from bs4 import BeautifulSoup
import requests


class CrackBiliBili():

    def __init__(self):
        self.url = "https://passport.bilibili.com/login"
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("disable-infobars")
        self.browser = webdriver.Chrome()
        self.browser.get(self.url)
        self.wait = WebDriverWait(self.browser, 20)
        self.username = USERNAME
        self.password = PASSWORD
        self.init_account()

    def init_account(self):
        un_input = self.wait.until(EC.presence_of_element_located((By.ID, 'login-username')))
        un_input.clear()
        un_input.send_keys(USERNAME)
        pw_input = self.wait.until(EC.presence_of_element_located((By.ID, 'login-passwd')))
        pw_input.clear()
        pw_input.send_keys(PASSWORD)

    def get_slider_button(self):
        """
        获取验证码滑块按钮
        :return: 按钮对象
        """
        slider = self.wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'gt_slider_knob')))
        return slider

    def get_bg_position(self):
        """
        获取又缺口的验证码图片位置
        :return: 缺口验证码图片位置集合
        """
        soup = BeautifulSoup(self.browser.page_source, 'html.parser')
        gt_cut_bg_slices = soup.find_all('div', class_='gt_cut_bg_slice')
        # 将图片下载下来
        u = re.findall('url."(.*?)".;', gt_cut_bg_slices[0]['style'], re.S)[0]
        resp = requests.get(u)
        with open('bg_image.jpg', 'wb') as f:
            f.write(resp.content)
        return self.get_postion(gt_cut_bg_slices)

    def get_fullbg_position(self):
        """
        获取完整验证码图片位置
        :return: 验证码图片位置集合
        """
        soup = BeautifulSoup(self.browser.page_source, 'html.parser')
        gt_cut_fullbg_slices = soup.find_all('div', class_="gt_cut_fullbg_slice")
        # 将图片下载下来
        u = re.findall('url."(.*?)".;', gt_cut_fullbg_slices[0]['style'], re.S)[0]
        resp = requests.get(u)
        with open('full_bg_image.jpg', 'wb') as f:
            f.write(resp.content)
        return self.get_postion(gt_cut_fullbg_slices)

    def get_postion(self, slices):
        """
        获取position
        :param slices: slice element
        :return: 集合
        """
        positions = []
        for i in slices:
            style = i['style']
            pattern = 'background-position: (.*?);'
            bg_position = re.findall(pattern, style, re.S)
            if len(bg_position) <= 0:
                continue
            position = bg_position[0].replace('px', '').split(' ')
            position = [int(i) for i in position]
            positions.append(position)
        return positions

    def cut_img(self, img, positions):
        """
        切割验证码图片
        :param img: 验证码的Image对象
        :param positions: 验证码的位置集合
        :return: 切割好的Image对象元组
        """
        first_line_img = []
        second_line_img = []

        for p in positions:
            if p[1] == -58:
                first_line_img.append(
                    img.crop(
                        (abs(p[0]), 58, abs(p[0]) + 10, 166)
                    ))
            else:
                second_line_img.append(
                    img.crop(
                        (abs(p[0]), 0, abs(p[0]) + 10, 58)
                    ))
        return first_line_img, second_line_img

    def merge_geetest_image(self, flp, slp):
        """
        合成验证码图片
        :param flp: 第一排图片数组
        :param slp: 第二排图片数组
        :return: Image对象
        """
        # 创建图片
        captcha = Image.new('RGB', (260, 116))
        offset_f = 0
        for f in flp:
            captcha.paste(f, (offset_f, 0))
            offset_f += f.size[0]

        offset_s = 0
        for s in slp:
            captcha.paste(s, (offset_s, 58))
            offset_s += s.size[0]

        return captcha

    def is_pixel_equal(self, image1, image2, x, y):
        """
        判断两个像素点是否相同
        :param image1: 图片1
        :param image2: 图片2
        :param x: 位置x
        :param y: 位置y
        :return: 像素是否相同
        """
        pixel1 = image1.load()[x, y]
        pixel2 = image2.load()[x, y]
        threshold = 60
        if abs(pixel1[0] - pixel2[0]) < threshold and abs(pixel1[1] - pixel2[1]) < threshold and abs(pixel1[2] - pixel2[2]) < threshold:
            return True
        else:
            return False

    def get_gap(self, full_image, bg_image):
        """
        获取验证码缺口偏移量
        :param full_image: 完整验证码
        :param bg_image: 有缺口验证码
        :return:
        """
        left = 0
        for i in range(left, full_image.size[0]):
            for j in range(full_image.size[1]):
                if not self.is_pixel_equal(full_image, bg_image, i, j):
                    left = i
                    return left
        return left

    def get_track(self, distance):
        """
        根据偏移量获取移动轨迹
        :param distance: 偏移量
        :return: 移动轨迹
        """
        # 移动轨迹
        track = []
        # 当前位移
        current = 0
        # 减速阈值
        mid = distance * 4 / 5
        # 计算间隔
        t = 0.2
        # 初速度
        v = 0

        while current < distance:
            if current < mid:
                # 加速度为正2
                a = 2
            else:
                # 加速度为负3
                a = -3
            # 初速度v0
            v0 = v
            # 当前速度v = v0 + at
            v = v0 + a * t
            # 移动距离x = v0t + 1/2 * a * t^2
            move = v0 * t + 1/2 * a * t * t
            # 当前位移
            current += move
            # 加入轨迹
            track.append(round(move))
        return track

    def reckon_trail(self, distance):  # 计算运动轨迹
        print('计算运动轨迹')
        track = []
        distance = int(distance) - 7  # 矫正值
        print('缺口坐标', distance)
        fast_distance = distance * (4 / 5)
        start, v0, t = 0, 0, 0.2
        while start < distance:
            if start < fast_distance:  # 加速状态
                a = 1.5  # 加速
            else:
                a = -3  # 减速
            # 数学公式 s=v0*t+1/2 v*t平方
            move = v0 * t + 1 / 2 * a * t * t
            # 当前速度
            v = v0 + a * t
            # 重置粗速度
            v0 = v
            # 重置起始位置
            start += move
            track.append(round(move))
        return track

    def move_to_gap(self, slider, track):
        """
        拖动滑块到缺口处
        :param slider: 滑块
        :param track: 轨迹
        :return:
        """
        ActionChains(self.browser).click_and_hold(slider).perform()
        for x in track:
            ActionChains(self.browser).move_by_offset(xoffset=x, yoffset=0).perform()
        time.sleep(0.5)
        ActionChains(self.browser).release().perform()


def main():
    cbb = CrackBiliBili()

    slider = cbb.get_slider_button()
    slider.click()
    s = cbb.get_screenshot()
    # s.show()

    # 完整验证码图
    fbg_pos = cbb.get_fullbg_position()
    fbg_img = Image.open("full_bg_image.jpg")
    fbg_flp, fbg_slp = cbb.cut_img(fbg_img, fbg_pos)
    fbg_img = cbb.merge_geetest_image(fbg_flp, fbg_slp)
    # fbg_img.show()

    # 缺口验证码图
    bg_pos = cbb.get_bg_position()
    bg_img = Image.open("bg_image.jpg")
    bg_flp, bg_slp = cbb.cut_img(bg_img, bg_pos)
    bg_img = cbb.merge_geetest_image(bg_flp, bg_slp)
    # bg_img.show()

    # 缺口偏移量
    distance = cbb.get_gap(fbg_img, bg_img)
    print("缺口偏移量: ", distance)

    # 移动轨迹
    track = cbb.get_track(distance - 7)
    print("移动轨迹: ", track)

    # 拖动滑块
    slider.click()
    time.sleep(10) # 等待几秒避免验证失败
    cbb.move_to_gap(slider, track)


if __name__ == '__main__':
    main()
