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


async def play(context, lecture_url):
    page = await context.new_page()

    await page.goto(lecture_url, wait_until="domcontentloaded")

    while True:
        try:
            await asyncio.sleep(3)
            main = page.frame("mainFrame")
            try:
                await main.click('.intro_enter_btn', timeout=7000)
            except PlaywrightError:
                print("Enter button did not appear, continuing without clicking...")

            await asyncio.sleep(1)
            player = page.frame("playerframe")

            await asyncio.sleep(1)

            async def playVid():
                # 재생
                try:
                    await player.wait_for_selector('.btn_common.btn_play', timeout=3000)
                    await asyncio.sleep(1)
                    await player.click('.btn_common.btn_play')
                except PlaywrightError:
                    print("Play button did not appear, continuing without clicking...")

            async def mute():
                try:
                    await player.wait_for_selector('.btn_mute', timeout=7000)
                    await asyncio.sleep(1)
                    await player.click('.btn_mute')
                    print("Mute button clicked successfully")
                except PlaywrightError:
                    print("Mute button did not appear, continuing without clicking...")

            async def change_playback_rate():
                try:
                    await player.wait_for_selector('.btn_speed18', timeout=10000)
                    await asyncio.sleep(1)
                    await player.click('.btn_speed18')
                    print("Playback rate changed successfully")
                except PlaywrightError:
                    print("Playback rate button did not appear, continuing without clicking...")

            await player.wait_for_selector('.control_text_status:has-text("재생 중")')
            # 비동기로 실행되도록 수정
            await asyncio.gather(
                playVid(),
                mute(),
                change_playback_rate()
            )
            # 최대 3시간
            await player.wait_for_selector('.currentbar[style*="width: 100%"]', timeout=10800000)

            try:
                total = await main.wait_for_selector("#totalPage")
                total = await total.text_content()
                current = await main.wait_for_selector("#currentPage")
                current = await current.text_content()

                if current != total:
                    await main.click("#nextBtn")
                elif current == total:
                    break
            except PlaywrightError:
                print("next안뜸")

        except:
            page.close()

    await page.close()
    await asyncio.sleep(1)


async def bootstrap():
    print("🚀 온라인 강의 자동 이어듣기 시작!\n")

    async with async_playwright() as p:
        browser = await p.firefox.launch(
            # True로 설정 시 창 표시 안함
            headless=True

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

                _id = pyautogui.prompt('숭싸대 아이디(학번) 입력')
                password = pyautogui.password('비밀번호')

            print("⏳ 로그인 중입니다 ...")

            playList = await authorization(context, LoginProps(_id, password))
            if playList:
                print(playList)
            else:
                print("들어야 할 강의가 없습니다.")
            for lecture_url in playList:
                await play(context, lecture_url)



            print("\n✋ 다음에 또 봐요!")

        except Exception as e:
            print(e)
        finally:
            await context.close()
            await browser.close()
            input()


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
