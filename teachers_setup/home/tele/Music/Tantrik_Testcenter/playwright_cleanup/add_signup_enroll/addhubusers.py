import asyncio
import re
import sys
from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright, username:str, password: str, rollno:str, host:str):
    response = {"success": False, "message": "Enrollment Not Successful"}
    try:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(f"http://{host}:8000/hub/login?next=%2Fhub%2F")
        await page.get_by_role("textbox", name="Username:").click()
        await page.get_by_role("textbox", name="Username:").fill(username)
        await page.get_by_role("textbox", name="Password:").click()
        await page.get_by_role("textbox", name="Password:").fill(password)
        await page.get_by_role("button", name="Sign In").click()
        await page.get_by_text("File", exact=True).click()
        async with page.expect_popup() as page1_info:
            await page.locator("#jp-mainmenu-file").get_by_text("Hub Control Panel").click()
        page1 = await page1_info.value
        await page1.get_by_role("link", name="Admin").click()
        await page1.get_by_role("button", name="Add Users").click()
        await page1.get_by_test_id("user-textarea").click()
        await page1.get_by_test_id("user-textarea").fill(rollno)
        await page1.get_by_test_id("submit").click()
        await page1.get_by_role("link", name="Admin").click()
        await page1.get_by_role("textbox", name="user-search").click()
        await page1.get_by_role("textbox", name="user-search").fill(username)
        await expect(page1.get_by_test_id(f"user-name-div-{username}")).to_be_visible()
        response["success"] = True
        response["message"] = "Hub Enrollment Success"
        await context.close()
        await browser.close()
    except Exception as e:
        print("Error occured while enroll in hub",str(e))
    return response



async def addhub_main(username:str, password:str, rollno:str, host:str) -> None:
    async with async_playwright() as playwright:
        res = await run(playwright, username, password,rollno, host)
        return res
    
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python script.py <username> <password> <rollno> <host>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    rollno = sys.argv[3]
    host = sys.argv[4]

    result = asyncio.run(addhub_main(username, password, rollno, host))
    print(result)



