import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict

class NaverMapRestaurantCrawler:
    def __init__(self, headless: bool = True):
        self.headless = headless
    
    async def crawl_single_page(self, search_query: str, page_num: int) -> List[Dict]:
        """특정 페이지 하나만 크롤링"""
        async with async_playwright() as p:
            # 프록시 설정 추가
            launch_options = {
                'headless': self.headless,
                'args': ['--no-sandbox', '--disable-dev-shm-usage']
            }
            
            browser = await p.chromium.launch(**launch_options)
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            await page.route("**/*.{png,jpg,jpeg,gif,svg,webp}", lambda route: route.abort())
            
            results = []
            
            try:
                await page.goto("https://map.naver.com/", wait_until="domcontentloaded")
                
                search_input = await page.wait_for_selector("input.input_search", state="visible")
                await search_input.click()
                await search_input.fill(search_query)
                await search_input.press("Enter")
                
                await page.wait_for_selector("iframe#searchIframe", state="visible")
                frame = page.frame("searchIframe")
                
                if not frame:
                    return results
                
                await frame.wait_for_selector("li.UEzoS", state="visible", timeout=10000)
                
                # 페이지 이동
                if page_num > 1:
                    page_link = await frame.query_selector(f"a.mBN2s:has-text('{page_num}')")
                    if page_link:
                        await page_link.click()
                        await frame.wait_for_selector("li.UEzoS", state="visible", timeout=5000)
                
                # 데이터 추출
                restaurants = await frame.query_selector_all("li.UEzoS")
                
                for restaurant in restaurants:
                    try:
                        name_elem = await restaurant.query_selector("span.TYaxT")
                        name = await name_elem.inner_text() if name_elem else "이름 없음"
                        
                        category_elem = await restaurant.query_selector("span.KCMnt")
                        category = await category_elem.inner_text() if category_elem else ""
                        
                        results.append({
                            '식당명': name,
                            '카테고리': category,
                            '페이지': page_num
                        })
                    except:
                        continue
                
                print(f"페이지 {page_num}: {len(restaurants)}개 수집")
                
            except Exception as e:
                print(f"페이지 {page_num} 크롤링 중 오류: {str(e)}")
            
            finally:
                await browser.close()
            
            return results

# 사용 예시
async def main():
    
    crawler = NaverMapRestaurantCrawler(headless=False)
    
    # 3개 페이지 동시 실행
    tasks = [
        crawler.crawl_single_page("공덕역 식당", 1),
        crawler.crawl_single_page("공덕역 식당", 2),
        crawler.crawl_single_page("공덕역 식당", 3)
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
        if item['식당명'] not in seen:
            seen.add(item['식당명'])
            unique_results.append(item)
    
    print(f"\n총 {len(unique_results)}개 식당 수집")
    for i, restaurant in enumerate(unique_results[:20], 1):
        print(f"{i}. {restaurant['식당명']} [{restaurant['카테고리']}]")

if __name__ == "__main__":
    asyncio.run(main())