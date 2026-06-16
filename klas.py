from playwright.sync_api import sync_playwright
from datetime import datetime
import re
import getpass

ID = input("학번 또는 사번을 입력해주세요 : ")
PW = getpass.getpass("비밀번호를 입력해주세요 : ")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    page.goto("https://klas.kw.ac.kr")

    page.fill("#loginId", ID)
    page.fill("#loginPwd", PW)

    page.click("button[type='submit']")

    page.wait_for_load_state("networkidle")

    today = datetime.today().date()

    items = page.query_selector_all("li > div")

    for item in items:
        spans = item.query_selector_all("span")

        if len(spans) < 2:
            continue

        full_date_text = spans[0].inner_text().strip()
        task_text = spans[1].inner_text().strip()

        # 날짜들 추출
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", full_date_text)

        if len(dates) < 2:
            continue

        end_date_text = dates[1]

        # 마지막 날짜만 비교
        end_date = datetime.strptime(end_date_text, "%Y-%m-%d").date()

        # 지난 과제면 제외
        if end_date < today:
            continue

        if "[과제]" in task_text:
            print(full_date_text)
            print(task_text)
            print("-" * 30)

    input("종료하려면 엔터")
