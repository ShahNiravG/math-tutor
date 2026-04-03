"""Canvas and OneLogin browser authentication helpers."""

from __future__ import annotations

import re
import time
from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


DEFAULT_TIMEOUT_SECONDS = 60
LOGIN_RENDER_TIMEOUT_MS = 20_000


def perform_login(
    *,
    page: Page,
    login_url: str,
    course_url: str,
    username: str,
    password: str,
) -> None:
    page.goto(login_url, wait_until="networkidle", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)

    if "onelogin.com" in page.url:
        perform_onelogin(page=page, username=username, password=password)
    else:
        perform_canvas_login(page=page, username=username, password=password)

    if not wait_for_login_completion(page):
        current_url = page.url
        if "/login" in current_url or "onelogin.com" in current_url:
            raise RuntimeError(
                f"Login did not complete successfully. Current page remained at {current_url}. "
                "Re-run with --headful to inspect the auth flow or finish any extra verification step."
            )
        page.goto(course_url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)
        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)

    current_url = page.url
    if "/login" in current_url or "onelogin.com" in current_url:
        login_error = extract_login_error(page)
        if login_error:
            raise RuntimeError(f"Canvas login failed: {login_error}")
        raise RuntimeError(
            "Login did not complete successfully. Re-run with --headful to inspect the flow."
        )

    page.goto(course_url, wait_until="networkidle", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)


def perform_canvas_login(*, page: Page, username: str, password: str) -> None:
    fill_first(
        page,
        [
            'input[name="pseudonym_session[unique_id]"]',
            'input[name="username"]',
            'input[type="email"]',
            'input[autocomplete="username"]',
            'input[placeholder*="Email" i]',
            'input[placeholder*="Username" i]',
            'input[aria-label*="Email" i]',
            'input[aria-label*="Username" i]',
            'input[type="text"]',
        ],
        username,
    )
    fill_first(
        page,
        [
            'input[name="pseudonym_session[password]"]',
            'input[name="password"]',
            'input[type="password"]',
            'input[autocomplete="current-password"]',
            'input[placeholder*="Password" i]',
            'input[aria-label*="Password" i]',
        ],
        password,
    )
    tick_checkbox_if_present(page)
    click_first(
        page,
        [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Log In")',
            'button:has-text("Login")',
            'button:has-text("Sign In")',
            'button:has-text("Next")',
        ],
    )


def perform_onelogin(*, page: Page, username: str, password: str) -> None:
    fill_first(
        page,
        [
            'input[name="username"]',
            'input[autocomplete="username"]',
            'input[type="email"]',
            'input[type="text"]',
        ],
        username,
    )
    click_first(
        page,
        [
            'button:has-text("Continue")',
            'button[type="submit"]',
            'input[type="submit"]',
        ],
    )

    password_locator = wait_for_any_locator(
        page,
        [
            'input[name="password"]',
            'input[autocomplete="current-password"]',
            'input[type="password"]',
        ],
        timeout_ms=LOGIN_RENDER_TIMEOUT_MS,
    )
    if password_locator is None:
        raise RuntimeError("OneLogin password field did not appear after submitting the username.")

    password_locator.fill(password)
    tick_checkbox_if_present(page)
    click_first(
        page,
        [
            'button:has-text("Continue")',
            'button[type="submit"]',
            'input[type="submit"]',
        ],
    )


def fill_first(page: Page, selectors: list[str], value: str) -> None:
    locator = wait_for_any_locator(page, selectors, timeout_ms=LOGIN_RENDER_TIMEOUT_MS)
    if locator is not None:
        locator.fill(value)
        return
    raise RuntimeError(f"Unable to find a login field matching selectors: {selectors}")


def click_first(page: Page, selectors: list[str]) -> None:
    locator = wait_for_any_locator(page, selectors, timeout_ms=LOGIN_RENDER_TIMEOUT_MS)
    if locator is not None:
        locator.click()
        return
    raise RuntimeError(f"Unable to find a submit control matching selectors: {selectors}")


def tick_checkbox_if_present(page: Page) -> None:
    locator = wait_for_locator_with_timeout(page, 'input[type="checkbox"]', timeout_ms=2_000)
    if locator is None:
        return
    if not locator.is_checked():
        locator.set_checked(True, force=True)


def extract_login_error(page: Page) -> str | None:
    error_patterns = [
        "Please verify your login or password and try again.",
        "Invalid login",
        "Incorrect password",
        "Unable to log in",
        "The email or password you entered is incorrect",
        "Your account is locked",
        "MFA required",
    ]
    for pattern in error_patterns:
        locator = page.get_by_text(pattern, exact=False)
        if locator.count() > 0:
            return locator.first.inner_text().strip()
    return None


def wait_for_login_completion(page: Page) -> bool:
    deadline = time.monotonic() + DEFAULT_TIMEOUT_SECONDS
    course_pattern = re.compile(r".*/courses/\d+.*")
    while time.monotonic() < deadline:
        if course_pattern.match(page.url):
            return True
        login_error = extract_login_error(page)
        if login_error:
            raise RuntimeError(f"Canvas login failed: {login_error}")
        page.wait_for_timeout(250)
    return False


def wait_for_locator(page: Page, selector: str) -> Any | None:
    return wait_for_locator_with_timeout(page, selector, timeout_ms=LOGIN_RENDER_TIMEOUT_MS)


def wait_for_any_locator(page: Page, selectors: list[str], timeout_ms: int) -> Any | None:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                if locator.count() > 0 and locator.is_visible():
                    return locator
            except PlaywrightTimeoutError:
                continue
        page.wait_for_timeout(250)
    return None


def wait_for_locator_with_timeout(page: Page, selector: str, timeout_ms: int) -> Any | None:
    locator = page.locator(selector).first
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return locator
    except PlaywrightTimeoutError:
        return None
