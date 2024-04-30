import asyncio
import logging
import os

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright._impl._api_types import Error as PlaywrightError
from service.auth import authorization, LoginProps

import pyautogui
import tkinter as tk
from service.dbUtil import DbUtil

import sqlite3

load_dotenv()

logging.basicConfig(level=logging.INFO)


def on_submit():
    global playList
    playList = [lecture for lecture, chk in zip(lectures, checkboxes) if chk.var.get() == 1]
    print("선택된 강의")
    printSelected = lambda i: [print(lecture.title) for lecture in i]
    printSelected(playList)
    root.destroy()


# Tkinter 윈도우 초기화
root = tk.Tk()
root.title("재생할 강의 선택")
root.wm_attributes("-topmost", 1)
root.iconify()

# 체크박스 및 변수 초기화
checkboxes = []
lectures = []
playList = []


async def play(context, component):
    page = await context.new_page()

    await page.goto(component.viewer_url, wait_until="domcontentloaded")
    await page.click('.vc-front-screen-play-btn', timeout=60000)

    async def mute():
        try:
            await page.wait_for_selector('.vc-pctrl-volume-btn', timeout=7000)
            await page.click('.vc-pctrl-volume-btn')
            print("Mute button clicked successfully")
        except PlaywrightError:
            print("Mute button did not appear, continuing without clicking...")

    async def confirm_actions():
        try:
            await page.wait_for_selector('.confirm-ok-btn', timeout=7000)
            await page.click('.confirm-ok-btn')
            print("Confirm button clicked successfully")
        except PlaywrightError:
            print("Confirm button did not appear, continuing without clicking...")

    async def change_playback_rate():
        try:
            await page.wait_for_selector('.vc-pctrl-playback-rate-toggle-btn', timeout=10000)
            await page.click('.vc-pctrl-playback-rate-toggle-btn')
            await page.wait_for_selector('#vc-pctrl-playback-rate-15', timeout=10000)
            await page.click('#vc-pctrl-playback-rate-15')
            print("Playback rate changed successfully")
        except PlaywrightError:
            print("Playback rate button did not appear, continuing without clicking...")

    # 비동기로 실행되도록 수정
    await asyncio.gather(
        mute(),
        confirm_actions(),
        change_playback_rate()
    )

    duration = component.item_content_data['duration'] - component.attendance_data['progress']
    duration *= 0.67
    await asyncio.sleep(duration)  # use asyncio.sleep for async function
    await page.close()
    await asyncio.sleep(1)


async def bootstrap():
    print("🚀 온라인 강의 자동 이어듣기 시작!\n")

    async with async_playwright() as p:
        browser = await p.firefox.launch(
            # True로 설정 시 창 표시 안함
            headless=False

        )
        context = await browser.new_context(
            locale="ko-KR",
        )
        try:
            os.environ["DEBUSSY"] = "1"
            _id = os.getenv("SSU_ID")
            password = os.getenv("SSU_PASSWORD")

            if not (_id and password):
                print("📝 로그인 정보를 입력하세요.")

                _id = pyautogui.prompt('lms 아이디(학번) 입력')
                password = pyautogui.password('비밀번호')

            print("⏳ 로그인 중입니다 ...")

            me = await authorization(context, LoginProps(_id, password))
            print(me)
            print("⏳ 강의 정보를 불러오는 중입니다 ...")

            print("\n✋ 다음에 또 봐요!")

        except Exception as e:
            print(e)
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    db = DbUtil()

    db.exec('''CREATE TABLE IF NOT EXISTS LECTURE_INFO (
                        id INTEGER PRIMARY KEY,
                        user_id TEXT,
                        term TEXT,
                        subject_info TEXT,
                        subject_code TEXT
                    )''')
    db.close()
    asyncio.run(bootstrap())
