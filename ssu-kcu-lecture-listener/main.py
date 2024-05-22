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


async def play(context, lecture):
    page = await context.new_page()
    lecture_url = lecture[0]
    title = lecture[1]
    await page.goto(lecture_url, wait_until="domcontentloaded")

    while True:
        try:
            await asyncio.sleep(3)
            main = page.frame("mainFrame")
            try:
                await main.click('.intro_enter_btn', timeout=7000)
            except PlaywrightError:
                pass

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
                    print("자동재생 되었습니다.")

            async def mute():
                try:
                    await player.wait_for_selector('.btn_mute', timeout=7000)
                    await asyncio.sleep(1)
                    await player.click('.btn_mute')
                    print("음소거 완료")
                except PlaywrightError:
                    print("Mute button did not appear, continuing without clicking...")

            async def change_playback_rate():
                try:
                    await player.wait_for_selector('.btn_speed18', timeout=10000)
                    await asyncio.sleep(1)
                    await player.click('.btn_speed18')
                    print("재생속도 1.8배 완료")
                except PlaywrightError:
                    print("Playback rate button did not appear, continuing without clicking...")

            await player.wait_for_selector('.control_text_status:has-text("재생 중")')
            # 비동기로 실행되도록 수정
            await asyncio.gather(
                playVid(),
                mute(),
                change_playback_rate()
            )
            current = await main.wait_for_selector("#currentPage")
            current = await current.text_content()
            print("")
            print("")
            while True:
                playback_rate = await player.evaluate('''() => {
                                const bar = document.querySelector('.currentbar');
                                return parseFloat(bar.style.width);
                            }''')
                print("", end="")
                print(f"\r{title} - {current}장 수강 중: {playback_rate}%", end="")
                await asyncio.sleep(1)  # 1초마다 체크
                if playback_rate >= 100:
                    break  # 재생이 100% 완료되었으면 반복 종료
            print("")
            print("")
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
            await page.close()

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
            if not playList:
                print("들어야 할 강의가 없습니다.")
            for lecture in playList:
                if lecture:
                    await play(context, lecture)

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
                        subject_code TEXT,
                        subject_title TEXT
                    )''')
    db.close()
    asyncio.run(bootstrap())
