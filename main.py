import asyncio
import logging
import os

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from service.auth import authorization, LoginProps

import pyautogui
import tkinter as tk
import sys
import io

load_dotenv()

logging.basicConfig(level=logging.INFO)

#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
#sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def bootstrap():
    print("🚀 온라인 강의 자동 이어듣기 시작!\n")

    async with async_playwright() as p:
        browser = await p.firefox.launch(
            # True로 설정 시 브라우저 창 안띄움
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

                _id = pyautogui.prompt('숭싸대 아이디(학번) 입력')
                password = pyautogui.password('비밀번호')

            print("⏳ 로그인 중입니다 ...")

            await authorization(context, LoginProps(_id, password))

            print("\n✋ 다음에 또 봐요!")

        except Exception as e:
            print(e)
        finally:
            await context.close()
            await browser.close()
            input()


if __name__ == "__main__":
    # db = DbUtil()
    #
    # db.exec('''CREATE TABLE IF NOT EXISTS LECTURE_INFO (
    #                     id INTEGER PRIMARY KEY,
    #                     user_id TEXT,
    #                     term TEXT,
    #                     subject_info TEXT,
    #                     subject_code TEXT,
    #                     subject_title TEXT
    #                 )''')
    # db.close()
    asyncio.run(bootstrap())
