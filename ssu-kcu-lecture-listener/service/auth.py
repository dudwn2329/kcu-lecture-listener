from collections import defaultdict

from playwright.sync_api import sync_playwright
from http.cookies import SimpleCookie
import re
import asyncio
from service.dbUtil import DbUtil

lecture_url = []


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
    global lecture_url
    db = DbUtil()
    login_page = await context.new_page()
    results = []
    await login_page.goto("https://www.kcu.ac/portal/default.asp", wait_until="domcontentloaded")
    # 로그인이동
    await login_page.evaluate('''() => {
                const newLink = document.createElement('a');
                const span = document.createElement('span');
                span.innerText = '로그인';
                newLink.appendChild(span);
                newLink.href = '/login/login.asp?loginType=01';
                document.body.appendChild(newLink);
            }''')
    await login_page.click('a[href="/login/login.asp?loginType=01"]')
    await login_page.wait_for_url("https://www.kcu.ac/login/login.asp?loginType=01", wait_until="domcontentloaded")
    # 학번 로그인이동
    await login_page.evaluate('''() => {
                    const newLink = document.createElement('a');
                    const span = document.createElement('span');
                    span.innerText = '로그인';
                    newLink.appendChild(span);
                    newLink.href = '/login/login.asp?loginType=05';
                    document.body.appendChild(newLink);
                }''')
    print("⏳ 강의 정보를 불러오는 중입니다 ...")
    await login_page.click('a[href="/login/login.asp?loginType=05"]')
    await login_page.wait_for_url("https://www.kcu.ac/login/login.asp?loginType=05", wait_until="domcontentloaded")

    await login_page.fill("#UserID", login_props.id)
    await login_page.fill("#Password", login_props.password)
    await login_page.click(".login_btn_type01")
    await login_page.wait_for_url("https://www.kcu.ac/2009/mycampus/student/index.asp?", wait_until="domcontentloaded")

    def handle_new_page(page):
        global lecture_url

        async def callback(page):
            new_url = page.url
            if "KcuLod" in new_url:
                lecture_url.append(new_url)

        asyncio.ensure_future(callback(page))

    unattended_weeks = defaultdict(list)
    code_set = set()
    qm_elements = await login_page.query_selector_all('img[src="/MyClass/student/sukang/images/qm.gif"]')
    for element in qm_elements:
        # 각 요소의 부모인 <a> 요소의 href 속성을 가져옵니다.
        href = await element.evaluate('(e) => e.closest("a").getAttribute("href")')

        # 주차 정보를 포함하는 상위 요소로 이동
        column_index = await element.evaluate('''el => {
                        const cell = el.closest("td");
                        const row = cell.parentElement;
                        return Array.from(row.children).indexOf(cell) - 1;
                    }''')

        # href 속성에서 termCode와 courseCode를 추출합니다.
        termCode = href.split('termCode=')[1].split('&')[0]
        courseCode = href.split('courseCode=')[1].split('&')[0]

        print("termCode:", termCode)
        print("courseCode:", courseCode)

        unattended_weeks[courseCode].append(column_index)
        code_set.add((termCode, courseCode))
    code_list = list(code_set)
    print("과목코드와 미수강 주차")
    print(unattended_weeks)
    print("Unique termCode and courseCode pairs:", code_list)

    for code in code_list:
        query = f"""
                SELECT TERM, SUBJECT_INFO,SUBJECT_CODE, USER_ID 
                FROM LECTURE_INFO
                WHERE 
                    TERM = ? AND SUBJECT_CODE = ? AND USER_ID = {login_props.id}
            """
        rows = db.getRows(query, code)
        if rows:
            for row in rows:
                for week in unattended_weeks[row[2]]:
                    attend_url = f'https://vod.kcu.or.kr/KcuLod/{row[0]}/{row[1]}/{row[2]}/{week}/index.html?userid={row[3]}'
                    results.append(attend_url)
                    print(attend_url)
        else:
            context.on("page", handle_new_page)
            url = f"https://www.kcu.ac/2009/mycampus/student/lecture/Plan/lectureplan.asp?termCode={code[0]}&courseCode={code[1]}"
            await login_page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            await login_page.click('a.btn-lec-play-stu:has-text("수강하기")')
            await asyncio.sleep(3)

    for url in lecture_url:
        user_id, semester_info, subject_info, subject_code = extract_info(url)
        print("URL:", url)
        print("학기 정보:", semester_info)
        print("과목 정보:", subject_info)
        print("과목 코드:", subject_code)

        if user_id and semester_info and semester_info and subject_code:
            query = f"""
                        INSERT INTO LECTURE_INFO (
                            user_id, 
                            term, 
                            subject_info, 
                            subject_code
                        ) VALUES (
                            ?, 
                            ?, 
                            ?, 
                            ?
                        )
            """
            db.exec(query=query, params=(user_id, semester_info, subject_info, subject_code))
        print("과목 정보를 저장했습니다. 다시 실행해주세요.")
    if db:
        db.close()
    return results


def extract_info(url):
    # URL에서 학기 정보, 과목 정보, 과목 코드, user_id를 추출합니다.
    pattern = r'KcuLod/(\d+)/(\d+)/([A-Z0-9]+)/.*?userid=(\d+)'
    match = re.search(pattern, url)
    if match:
        semester_info = match.group(1)
        subject_info = match.group(2)
        subject_code = match.group(3)
        user_id = match.group(4)
        return user_id, semester_info, subject_info, subject_code
    else:
        return None, None, None, None
