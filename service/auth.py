from collections import defaultdict

from playwright.sync_api import sync_playwright
from http.cookies import SimpleCookie
import re
import asyncio
from service.dbUtil import DbUtil
import threading

stop_flag = False

def wait_for_input():
    global stop_flag
    input("수강 도중에 프로그램을 종료하려면 Enter를 누르세요.\n")
    stop_flag = True



class LoginProps:
    def __init__(self, id: str, password: str):
        self.id = id
        self.password = password


class Authorization:
    def __init__(self, user_id: str, user_login: str, role: str, token: str):
        self.user_id = user_id
        self.user_login = user_login
        self.role = role
        self.token = token


async def authorization(context, login_props: LoginProps):
    login_page = await context.new_page()
    await login_page.goto("https://portal.kcu.ac/html/main/ssoko.html", wait_until="load", timeout=30000)
    await asyncio.sleep(1)
    # 로그인 화면에도 팝업이 있더라
    try:
        is_popup_displayed = await login_page.evaluate("window.getComputedStyle(document.querySelector('#idxPop')).display")
        if is_popup_displayed != "none":
            await login_page.click("#idxPop #close")
    except:
        pass
    await login_page.locator("#userId").wait_for(state="visible", timeout=10000)
    await login_page.fill("#userId", login_props.id)
    await login_page.fill("#userPw", login_props.password)
    await asyncio.sleep(1)
    await login_page.click("#loginBtnUserId")
    # 메인화면으로 이동이 되지 않으면 로그인 실패로 간주
    try:
        await login_page.wait_for_url("https://portal.kcu.ac/html/main/index.html?portalPage=portal_main", wait_until="domcontentloaded", timeout=5000)
    except:
        print('로그인 실패, 아이디와 비밀번호를 확인해주세요.')
        return


    subject_titles = {}
    print('로그인 성공!')
    await asyncio.sleep(1)


    # 팝업이 나올 경우 닫음
    try:
        is_popup_displayed = await login_page.evaluate("window.getComputedStyle(document.querySelector('#idxPop')).display")
        if is_popup_displayed != "none":
            await login_page.click("#idxPop #close")
            pass
        await asyncio.sleep(1)
    except:
        pass

    # 강의실 입장
    # 버튼이 안눌릴 때가 가끔 있음
    lectroom_btn = await login_page.wait_for_selector('.subject-name .btn-round-orange[tabindex="0"]')
    await lectroom_btn.hover()
    await lectroom_btn.click(delay=100)
    print('강의실 입장 중...')
    try:
        await login_page.wait_for_url("https://lms.kcu.ac/atnlcSubj/lectRoom", wait_until="load")
    except Exception as e:
        print('강의실 입장 중 에러 발생')
        print(e)

    # 필요한 정보 가져오기
    info = await login_page.evaluate('''
            () => {
                return {
                  shyr : $('#shyr').val(),
                  smstCd : $('#smstCd').val(),
                  coseCd : $('#coseCd').val(),
                  weekNo : $('#weekNo').val(),
                  empno : $('#profId').val(),
                  userAgent : userAgent(),
                  lectRmPrcsCd : lectRmPrcsCd,
                  userAuth : userAuth
               }
            } 
        ''')
    #print(info)

    # 각 수강과목 별로 프로세스 진행
    lnb = await login_page.query_selector_all(".subjLnb>a")
    # 입력 감지를 위한 쓰레드 시작
    input_thread = threading.Thread(target=wait_for_input)
    input_thread.start()
    for i in range(len(lnb)):
        if stop_flag:
            break
        lnb = await login_page.query_selector_all(".subjLnb>a")
        el = lnb[i]
    #for el in lnb:
        course_cd = await el.get_attribute("data-cose-cd")
        #print(course_cd)
        title = await el.text_content()
        await el.click()
        await asyncio.sleep(3)

        info['coseCd'] = course_cd

        # 과목 정보 화면으로 이동
        await studyList(login_page, info=info)

        await login_page.wait_for_url("https://lms.kcu.ac/atnlcSubj/atnlcApe/list", wait_until="load")


        print(f"{title} 수업 정보 읽는 중...")
        # 미수강 주차와 강의번호를 가져옴
        lectInfoList = await login_page.evaluate("""
            const elements = document.querySelectorAll('.btnLect');
            const dataAttributes = [];
            
            elements.forEach(element => {
                if (element.textContent.trim() === '이어보기' || element.textContent.trim() === '학습하기') {
                    const parentTr = element.closest('tr');
                    if (parentTr) {
                        dataAttributes.push({
                            weekNo: parentTr.getAttribute('data-week-no'),
                            lectNo: parentTr.getAttribute('data-lect-no')
                        });
                    }
                }
            });
            
            dataAttributes;
        """)
        print(lectInfoList)
        for item in lectInfoList:
            if stop_flag:
                break

            info['lectNo'] = item['lectNo']
            info['weekNo'] = item['weekNo']
            try:
                await lectRoom(login_page, info=info)
                await login_page.wait_for_url("https://lms.kcu.ac/atnlcSubj/lectRoom", wait_until="load")
                await login_page.wait_for_load_state("networkidle")
                # 로딩이 제대로 인식 안되는것 같아서 3초대기 박아버림
                await asyncio.sleep(3)

                frame = login_page.frame(name='cndIfram')
                if frame:
                    async def play():
                        await frame.evaluate('document.querySelector("video").play()')

                    async def mute():
                        await frame.evaluate('document.querySelector("video").muted = true')

                    async def change_playback_rate():
                        await frame.evaluate('document.querySelector("video").playbackRate = 2.0')

                    async def pause():
                        await frame.evaluate('document.querySelector("video").pause()')
                        await asyncio.sleep(2)

                    await asyncio.sleep(3)
                    print(f"{title} {info['weekNo']}주차 재생 중")
                    try:
                        await asyncio.gather(
                            play(),
                            mute(),
                            change_playback_rate()
                        )
                        # accTime은 실제 수강시간을 뜻함(초 단위)
                        accTime = await frame.evaluate('getParameter("AccTime")')
                        await frame.evaluate('''
                                (accTime) => {
                                    document.querySelector("video").currentTime = accTime
                                }
                            ''', accTime)

                        remaining_time = await frame.evaluate('''
                                () => {
                                    const video = document.querySelector("video");
                                    return (video.duration - video.currentTime);
                                }
                            ''')

                        # 비디오 완료 대기 및 루프 종료 확인
                        while True:
                            if stop_flag:
                                await pause()
                                print("사용자 입력을 감지했습니다. 프로그램을 종료합니다.")
                                break

                            playback_rate = await frame.evaluate('''
                                () => {
                                    const video = document.querySelector("video");
                                    return (video.currentTime / video.duration) * 100;
                                }
                            ''')
                            print(f"\r{playback_rate:.2f}%", end="")

                            await asyncio.sleep(1)  # 1초마다 체크
                            if playback_rate >= 100:
                                break  # 재생이 100% 완료되었으면 반복 종료

                        print("\n\n재생 완료")
                    except Exception as e:
                        print("재생 중 오류 발생:", e)
                        await pause()

                else:
                    print("프레임을 찾을 수 없습니다.")
            except Exception as e:
                print("수업 처리 중 오류 발생:", e)
                #await frame.wait_for_event("videoEnded", timeout=video_duration)



async def studyList(page, info):
    await page.wait_for_load_state('load')
    await page.evaluate('''
            (info)=> {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/atnlcSubj/atnlcApe/list';

                const shyr = document.createElement('input');
                shyr.type = 'text';
                shyr.name = 'shyr';
                shyr.value = info.shyr;

                const smstCd = document.createElement('input');
                smstCd.type = 'text';
                smstCd.name = 'smstCd';
                smstCd.value = info.smstCd;

                const coseCd = document.createElement('input');
                coseCd.type = 'text';
                coseCd.name = 'coseCd';
                coseCd.value = info.coseCd;

                const subjType = document.createElement('input');
                subjType.type = 'text';
                subjType.name = 'subjType';
                subjType.value = 'atnlcSubj';

                form.appendChild(shyr);
                form.appendChild(smstCd);
                form.appendChild(coseCd);
                form.appendChild(subjType);

                document.body.appendChild(form);
                form.submit();
            }
            ''', info)

async def lectRoom(page, info):
    await page.wait_for_load_state('load')
    await page.evaluate('''
                (info)=> {
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/atnlcSubj/lectRoom';

                    const shyr = document.createElement('input');
                    shyr.type = 'text';
                    shyr.name = 'shyr';
                    shyr.value = info.shyr;

                    const smstCd = document.createElement('input');
                    smstCd.type = 'text';
                    smstCd.name = 'smstCd';
                    smstCd.value = info.smstCd;

                    const coseCd = document.createElement('input');
                    coseCd.type = 'text';
                    coseCd.name = 'coseCd';
                    coseCd.value = info.coseCd;

                    const weekNo = document.createElement('input');
                    weekNo.type = 'text';
                    weekNo.name = 'weekNo';
                    weekNo.value = info.weekNo;
                    
                    const lectNo = document.createElement('input');
                    lectNo.type = 'text';
                    lectNo.name = 'lectNo';
                    lectNo.value = info.lectNo;
                    
                    const menuCd = document.createElement('input');
                    menuCd.type = 'text';
                    menuCd.name = 'menuCd';
                    menuCd.value = '04580'; 
                    
                    const currSub = document.createElement('input');
                    currSub.type = 'text';
                    currSub.name = 'currSub';
                    currSub.value = '04580';
                    
                    const prgmId = document.createElement('input');
                    prgmId.type = 'text';
                    prgmId.name = 'prgmId';
                    prgmId.value = 'LRN_LM_S_014';

                    form.appendChild(shyr);
                    form.appendChild(smstCd);
                    form.appendChild(coseCd);
                    form.appendChild(weekNo);
                    form.appendChild(lectNo);
                    form.appendChild(menuCd);
                    form.appendChild(currSub);
                    form.appendChild(prgmId);

                    document.body.appendChild(form);
                    form.submit();
                }
                ''', info)


