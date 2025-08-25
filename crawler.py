from datetime import datetime
import hashlib
import time
import os

import requests
from bs4 import BeautifulSoup

from board import Board
from database import SupabaseManager
from gpt_client import GPTClient

CRAWLING_URL_LIST = [
"https://computer.cnu.ac.kr/computer/notice/bachelor.do",
"https://computer.cnu.ac.kr/computer/notice/notice.do",
"https://computer.cnu.ac.kr/computer/notice/project.do",
"https://computer.cnu.ac.kr/computer/notice/cse.do",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://computer.cnu.ac.kr/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

def b_title_box_parser (item) :
    notice_data = {}

    link = item.select_one("a")
    if link:
        notice_data['title'] = link.get_text().strip()
        notice_data['url'] = link.get('href', '')

    # 새 글 여부 확인
    new_mark = item.select_one(".b-new span")
    notice_data['is_new'] = new_mark is not None

    # 세부 정보 추출
    m_con = item.select_one(".b-m-con")
    if m_con:
        # 공지 여부
        notice_mark = m_con.select_one(".b-notice")
        notice_data['is_notice'] = notice_mark is not None

        # 작성자
        writer = m_con.select_one(".b-writer")
        notice_data['writer'] = writer.get_text().strip() if writer else ""

        # 날짜
        date = m_con.select_one(".b-date")
        notice_data['date'] = date.get_text().strip() if date else ""

        # 조회수
        hit = m_con.select_one(".hit")
        notice_data['views'] = hit.get_text().strip().replace('조회수 ', '') if hit else "0"

    return notice_data

def make_pagination_url(page, url):
    offset = (page - 1) * 10
    return f"{url}?mode=list&&articleLimit=10&article.offset={offset}"


gpt = GPTClient()
db_manager = SupabaseManager()

def update_notice_schedules(deep_url: str, base_url: str):
    """
    기존 공지사항의 일정 정보를 가져와서 업데이트하는 함수
    """
    title = ""  # for exception logging
    try:
        # 상세 페이지로 이동하여 내용 가져오기
        deepResponse = requests.get(deep_url, headers=headers, timeout=10)
        deepResponse.raise_for_status()
        context = Board(boardHtml=deepResponse.text, baseUrl=base_url)

        title = context.title
        content = context.detail_text

        print(f"🔄 '{title}' 공지사항의 일정 정보 업데이트를 시작합니다.", flush=True)

        # GPT를 통해 일정 정보 추출
        schedules = gpt.extract_schedule_from_notice(title=title, content=content)

        # 추출된 일정이 있는 경우에만 DB 업데이트
        if schedules:
            db_manager.save_schedules(notice_title=title, schedules=schedules)
            print(f"✅ '{title}' 공지사항의 일정 {len(schedules)}건이 성공적으로 업데이트되었습니다.", flush=True)
        else:
            print(f"ℹ️ '{title}' 공지사항에서 추출할 일정이 없습니다.", flush=True)

    except requests.exceptions.RequestException as e:
        print(f"🔴 상세 페이지({deep_url})에 접근 중 오류 발생: {e}", flush=True)
    except Exception as e:
        error_title = f"'{title}' " if title else ""
        print(f"🔴 {error_title}공지사항의 일정 업데이트 처리 중 예외 발생({deep_url}): {e}", flush=True)



from typing import List, Dict

def discord_web_hook(notices: List[dict]):
    """새로운 공지사항들을 Discord webhook으로 전송합니다."""
    if not notices:
        return
    
    # 활성화된 webhook 총 개수 확인
    total_webhooks = db_manager.get_active_webhooks_count()
    
    if total_webhooks == 0:
        print("ℹ️ 활성화된 Discord webhook이 없습니다.")
        return
    
    print(f"📢 {len(notices)}개의 새로운 공지사항을 {total_webhooks}개의 webhook으로 배치 전송합니다.")
    
    batch_size = 50  # 한 번에 처리할 webhook 개수
    
    for notice in notices:
        markdown_content = notice.get('markdown_content') or "요약 내용이 없습니다."
        original_url_text = f"\n\n🔗 **원본 링크**: {notice.get('original_url', '')}"
        
        payload = {
            "content": markdown_content + original_url_text
        }
        
        # 배치 단위로 webhook 처리
        offset = 0
        batch_count = 0
        
        while True:
            webhook_batch = db_manager.get_active_webhooks_batch(batch_size=batch_size, offset=offset)
            
            if not webhook_batch:
                break
            
            batch_count += 1
            print(f"🔄 배치 {batch_count}: {len(webhook_batch)}개의 webhook 처리 중...")
            
            # 현재 배치의 webhook들에 전송
            for webhook in webhook_batch:
                try:
                    response = requests.post(webhook.url, json=payload, headers=headers, timeout=10)
                    response.raise_for_status()
                    print(f"✅ Webhook '{webhook.url[:50]}...'에 '{notice.get('title', '')[:30]}...' 전송 성공")
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 404:
                        print(f"🔴 Webhook '{webhook.url[:50]}...'이 존재하지 않습니다. 비활성화합니다.")
                        db_manager.deactivate_webhook(webhook.id)
                    else:
                        print(f"❌ Webhook '{webhook.url[:50]}...'에 전송 실패 (HTTP {response.status_code}): {e}")
                except Exception as e:
                    print(f"❌ Webhook 전송 중 예외 발생: {e}")
            
            offset += batch_size
            
            # 배치 간 짧은 대기 (서버 부하 방지)
            if webhook_batch:
                time.sleep(0.1)
        
        print(f"✅ '{notice.get('title', '')[:30]}...' 공지사항을 모든 webhook에 전송 완료")

def triggered_notice_exists(notices: List[dict]):
    discord_web_hook(notices)

# url String을 매개변수로 받아, 해당 사이트 html을 긁어와, 전체적인 파싱을 시작하는 함수
def crawler(url : str, page : int, category : int):
    response = requests.get(make_pagination_url(page, url), headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("div.b-title-box")

    # title, url, is_new, is_notice, writer, date, views 딕셔너리로 데이터 존재, 리스트임.
    items = list(map(b_title_box_parser, items))

    # print(*items, sep="\n")

    notices = []

    for item in items:
        if db_manager.notice_exists(title=item['title']) :
            # print(f"⚠️ '{item['title']}' 이전에 있는 공지사항입니다. 일정 정보 업데이트를 시도합니다.", flush=True)
            
            # deepUrl = url + item['url']
            # update_notice_schedules(deep_url=deepUrl, base_url=url)

            # time.sleep(10) # GPT API 호출 부하를 줄이기 위해 대기

            print(f"⚠️ '{item['title']}' 이전에 있는 공지사항입니다.", flush=True)
            continue

        deepUrl = url + item['url']
        deepResponse = requests.get(deepUrl, headers=headers, timeout=10)
        context = Board(boardHtml=deepResponse.text, baseUrl=url)

        print(deepUrl + " 로 접속하여 2차 크롤링을 진행합니다.", flush=True)

        ai_response = gpt.process_notice_content(title=context.title, content=context.detail_text)
        ai_schedules = gpt.extract_schedule_from_notice(title=context.title, content=context.detail_text)

        if (db_manager.notice_exists(title=context.title)) :
            print(f"⚠️ '{context.title}' 이전에 있는 공지사항입니다.", flush=True)
            continue

        # 2. DB에 저장할 데이터 준비
        try:
            # 날짜 문자열('YYYY-MM-DD' 또는 'YYYY.MM.DD')을 date 객체로 변환
            date_str = context.date.replace('.', '-')
            publish_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            publish_date_obj = None  # 날짜 파싱 실패 또는 날짜 정보가 없는 경우 None으로 처리

        # models.Notice에 맞는 데이터 구조 생성
        notice_data = {
            'title': context.title,
            'content': context.detail_text,
            'writer': context.writer,
            'writer_email': context.email,
            'publish_date': publish_date_obj,
            'is_notice': item.get('is_notice', False),
            'ai_summary_title': ai_response.AI_SUMMARY_TITLE,
            'ai_summary_content': ai_response.AI_SUMMARY_CONTENT,
            'markdown_content': ai_response.MARKDOWN_CONTENT,
            'original_url': deepUrl,
            'category': category,
        }

        # 3. 데이터베이스에 공지사항 및 이미지 정보 저장
        try:
            notice = db_manager.save_notice(notice_data=notice_data, image_urls=context.images, files=context.file_box, ai_schedules=ai_schedules)
        except Exception as e:
            print(f"🔴 데이터베이스 저장 중 오류 발생: {e}")
            raise
            
        notices.append(notice)  # notice는 dict
        time.sleep(5)
    
    triggered_notice_exists(notices)

def discord_web_hook_admin(error_message: str):
    """관리자용 Discord Webhook으로 에러 메시지 전송"""

    admin_webhook_url = os.getenv("DISCORD_ADMIN_WEBHOOK_URL")

    if not admin_webhook_url:
        print("❗ 관리자용 Discord Webhook URL이 설정되어 있지 않습니다.")
        return

    payload = {
        "content": f"🚨 **크롤러 에러 발생!**\n```\n{error_message}\n```"
    }

    try:
        response = requests.post(admin_webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print("✅ 에러 메시지를 관리자 Discord Webhook으로 전송했습니다.")
    except Exception as e:
        print(f"❌ 관리자 Discord Webhook 전송 실패: {e}")

def main():
    category = 0
    for url in CRAWLING_URL_LIST:
        try:
            crawler(url, 1, category)
        except Exception as e:
            error_message = f"[{url}] {str(e)}"
            discord_web_hook_admin(error_message)
            print(e, "에러로 인해, 시스템 중지.")
            return
        category += 1
        time.sleep(5)

if __name__ == '__main__':
    main()