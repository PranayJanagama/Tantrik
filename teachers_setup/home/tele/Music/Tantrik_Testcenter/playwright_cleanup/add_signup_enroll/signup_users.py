import asyncio
import sys
import re
from playwright.async_api import Playwright, async_playwright, expect

async def run(playwright: Playwright, rollno:str, host:str) -> None:
    response = {"success": False, "message": "Enrollment Not Successful"}
    try:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(f"http://{host}:8000/hub/login?next=%2Fhub%2F")
        await page.get_by_role("link", name="Sign up").click()
        await page.get_by_role("textbox", name="Username:").click()
        await page.get_by_role("textbox", name="Username:").fill(rollno)
        await page.get_by_role("textbox", name="Password:").click()
        await page.get_by_role("textbox", name="Password:").fill(rollno)
        await page.locator("#password_confirmation_input").click()
        await page.locator("#password_confirmation_input").fill(rollno)
        await page.get_by_role("button", name="Create User").click()
        await expect(page.get_by_text("The signup was successful!")).to_be_visible()
        response["success"] = True
        response["message"] = "SignUp user Success"
        await context.close()
        await browser.close()
    except Exception as e:
        print("Error in signup user",str(e))
    return response

async def signup_main(rollno:str, host:str) -> None:
    async with async_playwright() as playwright:
        return await run(playwright, rollno, host)