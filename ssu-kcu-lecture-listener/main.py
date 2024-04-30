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

# Tkinter 윈도우 초기화
root = tk.Tk()
root.title("재생할 강의 선택")
root.wm_attributes("-topmost", 1)
root.iconify()

# 체크박스 및 변수 초기화
checkboxes = []
lectures = []


async def play(context, lecture_url):
    page = await context.new_page()

    await page.goto(lecture_url, wait_until="domcontentloaded")

    while True:
        await asyncio.sleep(3)
        main = page.frame("mainFrame")
        try:
            await main.click('.intro_enter_btn', timeout=7000)
        except PlaywrightError:
            print("Enter button did not appear, continuing without clicking...")

        await asyncio.sleep(1)
        player = page.frame("playerframe")

        await asyncio.sleep(1)

        try:
            await player.wait_for_selector('.btn_common.btn_play', timeout=7000)
            await player.click('.btn_common.btn_play')
        except PlaywrightError:
            print("Play button did not appear, continuing without clicking...")

        async def mute():
            try:
                await player.wait_for_selector('.btn_mute', timeout=7000)
                await player.click('.btn_mute')
                print("Mute button clicked successfully")
            except PlaywrightError:
                print("Mute button did not appear, continuing without clicking...")

        async def change_playback_rate():
            try:
                await player.wait_for_selector('.btn_speed20', timeout=10000)
                await player.click('.btn_speed20')
                print("Playback rate changed successfully")
            except PlaywrightError:
                print("Playback rate button did not appear, continuing without clicking...")

        # 비동기로 실행되도록 수정
        await asyncio.gather(
            mute(),
            change_playback_rate()
        )
        await player.wait_for_selector('.currentbar[style*="width: 100%"]', timeout=300000)

        total = await main.wait_for_selector("#totalPage")
        total = await total.text_content()
        current = await main.wait_for_selector("#currentPage")
        current = await current.text_content()
        if current != total:
            await main.click("#nextBtn")
        elif current == total:
            break

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

            playList = await authorization(context, LoginProps(_id, password))
            print(playList)
            for lecture_url in playList:
                await play(context, lecture_url)

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
