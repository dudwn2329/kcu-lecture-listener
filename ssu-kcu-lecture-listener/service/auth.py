from playwright.sync_api import sync_playwright
from http.cookies import SimpleCookie

import asyncio

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


async def authorization(context, login_props: LoginProps) -> Authorization:
    global lecture_url
    login_page = await context.new_page()
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
    await login_page.click('a[href="/login/login.asp?loginType=05"]')
    await login_page.wait_for_url("https://www.kcu.ac/login/login.asp?loginType=05", wait_until="domcontentloaded")

    await login_page.fill("#UserID", login_props.id)
    await login_page.fill("#Password", login_props.password)
    await login_page.click(".login_btn_type01")
    await login_page.wait_for_url("https://www.kcu.ac/2009/mycampus/student/index.asp?", wait_until="domcontentloaded")

    def handle_new_page(page):
        global lecture_url

        async def callback(page):
            url = page.url
            if "KcuLod" in url:
                lecture_url.append(page.url)
            await page.close()

        asyncio.ensure_future(callback(page))

    code_set = set()
    qm_elements = await login_page.query_selector_all('img[src="/MyClass/student/sukang/images/qm.gif"]')
    for element in qm_elements:
        # 각 요소의 부모인 <a> 요소의 href 속성을 가져옵니다.
        href = await element.evaluate('(e) => e.closest("a").getAttribute("href")')

        # href 속성에서 termCode와 courseCode를 추출합니다.
        termCode = href.split('termCode=')[1].split('&')[0]
        courseCode = href.split('courseCode=')[1].split('&')[0]

        print("termCode:", termCode)
        print("courseCode:", courseCode)
        code_set.add((termCode, courseCode))
    code_list = list(code_set)
    print("Unique termCode and courseCode pairs:", code_list)
    await asyncio.sleep(3)  # 결과 확인을 위해 잠시 대기합니다.
    context.on("page", handle_new_page)
    for code in code_list:
        url = f"https://www.kcu.ac/2009/mycampus/student/lecture/Plan/lectureplan.asp?termCode={code[0]}&courseCode={code[1]}"
        await login_page.goto(url, wait_until="domcontentloaded")
        element = await login_page.click('a.btn-lec-play-stu:has-text("수강하기")')
        await asyncio.sleep(30)
        print(lecture_url)
    """
    qm_elements = await login_page.query_selector_all('img[src="/MyClass/student/sukang/images/qm.gif"]')
    for element in qm_elements:
        # 각 qm.gif 이미지를 포함하는 <a> 요소의 부모의 부모인 <a> 요소의 자바스크립트를 실행하여 팝업을 엽니다.
        await element.evaluate_handle('e => e.closest("a").click()')
        await asyncio.sleep(5)
        # 팝업이 열릴 때까지 대기합니다.
        await login_page.goto("https://www.kcu.ac/2009/mycampus/student/lecture/leture_main.asp", wait_until="domcontentloaded")

        # 팝업 창의 내용을 가져옵니다.
        popup_content = await login_page.content()
        print("Popup content:", popup_content)
        "https://www.kcu.ac/2009/mycampus/student/lecture/Plan/lectureplan.asp?termCode=20241&courseCode=XE402201"
        await asyncio.sleep(300)
    """
