import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict
import traceback


class NaverMapRestaurantCrawler:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def crawl_single_page(self, search_query: str, page_num: int) -> List[Dict]:
        """특정 페이지 하나만 크롤링"""
        async with async_playwright() as p:
            # 프록시 설정 추가
            launch_options = {
                "headless": self.headless,
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-web-security",
                    "--disable-site-isolation-trials",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--safebrowsing-disable-auto-update",
                    "--ignore-certificate-errors",
                    "--ignore-ssl-errors",
                    "--ignore-certificate-errors-spki-list",
                    "--disable-setuid-sandbox",
                    "--window-size=1920,1080",
                    "--start-maximized",
                ],
            }

            browser = await p.chromium.launch(**launch_options)

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                locale="ko-KR",
                timezone_id="Asia/Seoul",
                permissions=["geolocation"],
                geolocation={"latitude": 37.5665, "longitude": 126.9780},  # 서울
                color_scheme="light",
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "max-age=0",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                    "Sec-Fetch-Dest": "document",
                    "Upgrade-Insecure-Requests": "1",
                },
            )
            page = await context.new_page()

            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,webp}", lambda route: route.abort()
            )

            results = []

            try:
                await page.goto("https://map.naver.com/", wait_until="domcontentloaded")

                search_input = await page.wait_for_selector(
                    "input.input_search", state="visible"
                )
                await search_input.click()
                await search_input.fill(search_query)
                await search_input.press("Enter")

                await page.wait_for_selector(
                    "iframe#searchIframe", state="visible", timeout=100000
                )
                iframe_element = await page.query_selector("iframe#searchIframe")

                frame = await iframe_element.content_frame()

                if frame:
                    previous_count = 0
                    no_change_count = 0
                    max_no_change = 3  # 3번 연속으로 변화가 없으면 종료

                    while True:
                        # 현재 로드된 식당 수 확인
                        current_restaurants = await frame.query_selector_all("li.UEzoS")
                        current_count = len(current_restaurants)

                        # 변화가 없으면 카운트 증가
                        if current_count == previous_count:
                            no_change_count += 1

                            if no_change_count >= max_no_change:
                                print("더 이상 로드할 데이터가 없습니다.")
                                break
                        else:
                            no_change_count = 0  # 변화가 있으면 카운트 리셋

                        previous_count = current_count

                        # 스크롤 실행
                        await frame.evaluate(
                            """
                            () => {
                                const scrollContainer = document.querySelector('.Ryr1F') || 
                                                       document.querySelector('[role="main"]') || 
                                                       document.body;
                                
                                if (scrollContainer) {
                                    scrollContainer.scrollTop = scrollContainer.scrollHeight;
                                } else {
                                    window.scrollTo(0, document.body.scrollHeight);
                                }
                            }
                        """
                        )

                        # 새로운 데이터 로딩 대기
                        await asyncio.sleep(2)

                if not frame:
                    return results

                await frame.wait_for_selector(
                    "li.UEzoS", state="visible", timeout=100000
                )

                # 페이지 이동
                if page_num > 1:
                    page_link = await frame.query_selector(
                        f"a.mBN2s:has-text('{page_num}')"
                    )
                    if not page_link:
                        raise Exception("해당 페이지 없음")
                    await page_link.click()
                    await asyncio.sleep(3)
                    await frame.wait_for_selector(
                        "li.UEzoS", state="visible", timeout=100000
                    )

                # 데이터 추출
                restaurants = await frame.query_selector_all("li.UEzoS")

                for restaurant in restaurants:
                    try:
                        name_elem = await restaurant.query_selector("span.TYaxT")
                        name = (
                            await name_elem.inner_text() if name_elem else "이름 없음"
                        )

                        category_elem = await restaurant.query_selector("span.KCMnt")
                        category = (
                            await category_elem.inner_text() if category_elem else ""
                        )
                        place_id = None
                        link_elem = await restaurant.query_selector("a.place_bluelink")
                        print(link_elem)
                        if link_elem:
                            # 현재 URL 저장
                            current_url = page.url

                            # 새 탭에서 열기를 방지하기 위해 target 속성 제거
                            await link_elem.evaluate(
                                '(el) => el.removeAttribute("target")'
                            )

                            # 클릭
                            await link_elem.click()

                            # URL 변경 대기 (최대 3초)
                            await page.wait_for_url(
                                lambda url: "/place/" in url, timeout=3000
                            )

                            # 변경된 URL에서 place ID 추출
                            new_url = page.url
                            print(new_url)
                            import re

                            match = re.search(r"/place/(\d+)", new_url)
                            if match:
                                place_id = match.group(1)

                        results.append(
                            {
                                "place_id": place_id,
                                "식당명": name,
                                "카테고리": category,
                                "페이지": page_num,
                            }
                        )
                    except:
                        continue
                print(f"페이지 {page_num}: {len(restaurants)}개 수집")

            except Exception as e:
                traceback.print_exc()
                print(f"페이지 {page_num} 크롤링 중 오류: {str(e)}")
            finally:
                await browser.close()
            return results


# 사용 예시
async def main():

    crawler = NaverMapRestaurantCrawler(headless=True)

    # 3개 페이지 동시 실행
    tasks = [
        crawler.crawl_single_page("공덕역 식당", 1),
        # crawler.crawl_single_page("공덕역 식당", 2),
        # crawler.crawl_single_page("공덕역 식당", 3),
    ]

    # 모든 결과 대기
    all_results = await asyncio.gather(*tasks)

    # 결과 병합 및 중복 제거
    merged_results = []
    for page_results in all_results:
        merged_results.extend(page_results)

    unique_results = []
    seen = set()
    for item in merged_results:
        if item["place_id"] not in seen:
            seen.add(item["place_id"])
            unique_results.append(item)

    print(f"\n총 {len(unique_results)}개 식당 수집")
    for i, restaurant in enumerate(unique_results, 1):
        print(
            f"{i}. {restaurant['place_id']} [{restaurant['식당명']} [{restaurant['카테고리']}] [{restaurant['페이지']}]"
        )


if __name__ == "__main__":
    asyncio.run(main())
