from sqlite3 import Date
from postgrest import CountMethod
from gpt_client import ScheduleItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Notice, NoticeImage, NoticeFile, Schedule, Webhook
import hashlib
from typing import Optional, List, cast
import os
from dotenv import load_dotenv
from typing import List, Dict
from datetime import date, datetime
from supabase import create_client, Client

load_dotenv()

# class DatabaseManager:
#     def __init__(self, db_url: str | None = None):
#         if not db_url:
#             db_url = os.getenv('DATABASE_URL')

#         assert db_url is not None
        
#         self.engine = create_engine(db_url, echo=False)
#         self.SessionLocal = sessionmaker(bind=self.engine)

#         Base.metadata.create_all(self.engine)
        
#     def create_tables(self):
#         """테이블 생성"""
#         Base.metadata.create_all(self.engine)
#         print("✅ 데이터베이스 테이블이 생성되었습니다.")

#     def get_session(self) -> Session:
#         """세션 반환"""
#         return self.SessionLocal()
    
#     def get_title_hash(self, title: str) -> str:
#         """제목을 해시로 변환"""
#         return hashlib.sha256(title.encode('utf-8')).hexdigest()
    
#     def notice_exists(self, title: str) -> bool:
#         """공지사항 존재 여부 확인 (해시 기반)"""
#         title_hash = self.get_title_hash(title)
#         with self.get_session() as session:
#             return session.query(Notice).filter(Notice.title_hash == title_hash).first() is not None

#     def get_active_webhooks(self) -> List[Webhook]:
#         """활성화된 webhook 목록을 가져옵니다."""
#         with self.get_session() as session:
#             return session.query(Webhook)\
#                          .filter(Webhook.is_active == True)\
#                          .all()

#     def get_active_webhooks_batch(self, batch_size: int = 50, offset: int = 0) -> List[Webhook]:
#         """활성화된 webhook 목록을 배치 단위로 가져옵니다."""
#         with self.get_session() as session:
#             return session.query(Webhook)\
#                          .filter(Webhook.is_active == True)\
#                          .offset(offset)\
#                          .limit(batch_size)\
#                          .all()

#     def get_active_webhooks_count(self) -> int:
#         """활성화된 webhook의 총 개수를 반환합니다."""
#         with self.get_session() as session:
#             return session.query(Webhook)\
#                          .filter(Webhook.is_active == True)\
#                          .count()

#     def deactivate_webhook(self, webhook_id: int):
#         """webhook을 비활성화합니다."""

#         with self.get_session() as session:
#             try:
#                 webhook = session.query(Webhook).filter(Webhook.id == webhook_id).first()
#                 assert webhook is not None

#                 if webhook:
#                     webhook.is_active = False
#                     session.commit()
#                     print(f"🔴 Webhook ID {webhook_id}를 비활성화했습니다.")
#                 else:
#                     print(f"⚠️ Webhook ID {webhook_id}를 찾을 수 없습니다.")
#             except Exception as e:
#                 session.rollback()
#                 print(f"❌ Webhook 비활성화 실패 (ID: {webhook_id}): {e}")
#                 raise

#     def save_schedules(self, notice_title: str, schedules: List[Dict[str, str]]):
#         """
#         공지사항 제목을 기반으로 일정을 찾아 저장하거나 업데이트합니다.
#         기존에 있던 일정은 모두 삭제하고 새로운 일정을 저장합니다.
#         """
#         with self.get_session() as session:
#             try:
#                 # 1. 제목 해시를 사용하여 공지사항을 찾습니다.
#                 title_hash = self.get_title_hash(notice_title)
#                 notice = session.query(Notice).filter(Notice.title_hash == title_hash).first()

#                 if not notice:
#                     print(f"⚠️ 공지사항을 찾을 수 없습니다: {notice_title}")
#                     return

#                 # 2. 기존 일정을 모두 삭제합니다.

#                 if notice.schedules:
#                     print(f"🔄 '{notice.title}'의 기존 일정 {len(notice.schedules)}개를 삭제합니다.")
#                     del notice.schedules[:]
                
#                 # 3. 새로운 일정 정보를 추가합니다.
#                 for sched_data in schedules:
#                     schedule = Schedule(
#                         title=sched_data['title'],
#                         description=sched_data.get('description'),
#                         begin=datetime.fromisoformat(sched_data['begin']),
#                         end=datetime.fromisoformat(sched_data['end']),
#                         notice_id=notice.id  # 명시적으로 notice_id 설정
#                     )
#                     session.add(schedule)
                
#                 session.commit()
#                 print(f"✅ '{notice.title}'에 새로운 일정 {len(schedules)}개를 저장했습니다.")

#             except Exception as e:
#                 session.rollback()
#                 print(f"❌ 일정 저장 실패 ({notice_title}): {e}")
#                 raise

#     def save_notice(self, notice_data: dict, image_urls: List[str] = None, files: List[Dict[str, str]] = None, ai_schedules: List[Dict[str, str]] = None) -> Notice:
#         """공지사항 저장"""
#         with self.get_session() as session:
#             try:
#                 # 공지사항 생성
#                 notice = Notice(
#                     title=notice_data['title'],
#                     content=notice_data['content'],
#                     writer=notice_data.get('writer'),
#                     writer_email=notice_data.get('writer_email'),
#                     publish_date=notice_data.get('publish_date'),
#                     is_notice=notice_data.get('is_notice', False),
#                     ai_summary_title=notice_data.get('ai_summary_title'),
#                     ai_summary_content=notice_data.get('ai_summary_content'),
#                     markdown_content=notice_data.get('markdown_content'),
#                     original_url=notice_data['original_url'],
#                     ignore_flag=notice_data.get('ignore_flag', False),
#                     title_hash=self.get_title_hash(notice_data['title']),
#                     category=notice_data['category']
#                 )
                
#                 session.add(notice)
#                 session.flush()  # ID 생성을 위해
                
#                 # 일정 정보 추가 (새 공지사항 저장 시)
#                 if ai_schedules:
#                     for sched_data in ai_schedules:
#                         schedule = Schedule(
#                             title=sched_data['title'],
#                             description=sched_data.get('description'),
#                             begin=datetime.fromisoformat(sched_data['begin']),
#                             end=datetime.fromisoformat(sched_data['end']),
#                             notice_id=notice.id
#                         )
#                         notice.schedules.append(schedule)
                
#                 # 이미지 저장
#                 if image_urls:
#                     for img_url in image_urls:
#                         image = NoticeImage(
#                             url=img_url,
#                             notice_id=notice.id
#                         )
#                         session.add(image)

#                 if files:
#                     for file in files:
#                         fileEntity = NoticeFile(
#                             filename = file['file_name'],
#                             url = file['download_link'],
#                             notice_id = notice.id
#                         )

#                         session.add(fileEntity)

                
#                 session.commit()
#                 print(f"✅ 공지사항 저장 완료: {notice_data['title'][:50]}...")
#                 session.refresh(notice)  # 새로 생성된 공지사항 객체를 갱신
#                 return notice
                
#             except Exception as e:
#                 session.rollback()
#                 print(f"❌ 공지사항 저장 실패: {e}")
#                 raise
    
#     def get_recent_notices(self, limit: int = 10) -> List[Notice]:
#         """최근 공지사항 조회"""
#         with self.get_session() as session:
#             return session.query(Notice)\
#                          .order_by(Notice.created_at.desc())\
#                          .limit(limit).all()



class SupabaseManager:
    def __init__(self):
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")

        assert SUPABASE_URL is not None
        assert SUPABASE_KEY is not None

        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def get_title_hash(self, title: str) -> str:
        return hashlib.sha256(title.encode('utf-8')).hexdigest()

    def notice_exists(self, title: str) -> bool:
        title_hash = self.get_title_hash(title)
        response = self.client.table("notice").select("id").eq("title_hash", title_hash).limit(1).execute()
        print(title, response.data)
        return bool(response.data)

    def get_active_webhooks(self) -> list:
        response = self.client.table("webhooks").select("*").eq("is_active", True).execute()
        return [Webhook(**row) for row in response.data]

    def get_active_webhooks_batch(self, batch_size: int = 50, offset: int = 0) -> list:
        response = (
            self.client.table("webhooks")
            .select("*")
            .eq("is_active", True)
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        return [Webhook(**row) for row in response.data]

    def get_active_webhooks_count(self) -> int:
        response = self.client.table("webhooks").select("id", count=CountMethod.exact).eq("is_active", True).execute()
        return response.count or 0

    def deactivate_webhook(self, webhook_id: int):
        response = (
            self.client.table("webhooks")
            .update({"is_active": False})
            .eq("id", webhook_id)
            .execute()
        )
        if response.data:
            print(f"🔴 Webhook ID {webhook_id}를 비활성화했습니다.")
        else:
            print(f"⚠️ Webhook ID {webhook_id}를 찾을 수 없습니다.")

    def save_schedules(self, notice_title: str, schedules: list):
        title_hash = self.get_title_hash(notice_title)
        notice_resp = self.client.table("notice").select("id").eq("title_hash", title_hash).limit(1).execute()
        if not notice_resp.data:
            print(f"⚠️ 공지사항을 찾을 수 없습니다: {notice_title}")
            return
        notice_id = notice_resp.data[0]["id"]
        # 기존 일정 삭제
        old_scheds = self.client.table("schedules").select("id").eq("notice_id", notice_id).execute()
        for sched in old_scheds.data:
            self.client.table("schedules").delete().eq("id", sched["id"]).execute()
        # 새 일정 추가
        from datetime import datetime
        for sched_data in schedules:
            self.client.table("schedules").insert({
                "title": sched_data["title"],
                "description": sched_data.get("description"),
                "begin": sched_data["begin"],
                "end": sched_data["end"],
                "notice_id": notice_id,
                "created_at": datetime.now().isoformat()
            }).execute()
        print(f"✅ '{notice_title}'에 새로운 일정 {len(schedules)}개를 저장했습니다.")

    def save_notice(self, notice_data: dict,
                    image_urls: Optional[List[str]] = None,
                    files: Optional[List[Dict[str, str]]] = None,
                    ai_schedules: Optional[List[ScheduleItem]] = None,
                    original_title: str = None) -> dict:
        """공지사항 저장 (항상 dict 리턴)"""
        try:
            # 공지사항 먼저 insert
            title_hash = self.get_title_hash(original_title) if original_title else self.get_title_hash(notice_data['title'])

            notice_payload = {
                "title": notice_data['title'],
                "content": notice_data['content'],
                "writer": notice_data.get('writer'),
                "writer_email": notice_data.get('writer_email'),
                # date 객체라면 isoformat()으로 변환, 아니면 그대로
                "publish_date": cast(date, notice_data.get('publish_date')).isoformat() if notice_data.get('publish_date') else None,
                "is_notice": notice_data.get('is_notice', False),
                "ai_summary_title": notice_data.get('ai_summary_title'),
                "ai_summary_content": notice_data.get('ai_summary_content'),
                "markdown_content": notice_data.get('markdown_content'),
                "original_url": notice_data['original_url'],
                "ignore_flag": notice_data.get('ignore_flag', False),
                "title_hash": title_hash,
                "category": notice_data['category'],
            }

            notice_result = self.client.table("notice").insert(notice_payload).execute()
            notice_id = notice_result.data[0]['id']
            result_dict = dict(notice_result.data[0])  # 항상 dict로 변환

            # 일정 insert
            if ai_schedules:
                schedule_payload = []
                for s in ai_schedules:
                    schedule_payload.append({
                        "title": s.title,
                        "description": s.description,
                        "begin": s.begin,
                        "end": s.end,
                        "notice_id": notice_id,
                        "is_ignored": False  # NOT NULL 컬럼 기본값 추가
                    })
                schedules_result = self.client.table("schedules").insert(schedule_payload).execute()
                result_dict["schedules"] = [dict(row) for row in getattr(schedules_result, 'data', [])]

            # 이미지 insert
            if image_urls:
                img_payload = [{"url": url, "notice_id": notice_id} for url in image_urls]
                images_result = self.client.table("notice_images").insert(img_payload).execute()
                result_dict["images"] = [dict(row) for row in getattr(images_result, 'data', [])]

            # 파일 insert
            if files:
                file_payload = [{
                    "filename": f["file_name"],
                    "url": f["download_link"],
                    "notice_id": notice_id
                } for f in files]
                files_result = self.client.table("notice_files").insert(file_payload).execute()
                result_dict["files"] = [dict(row) for row in getattr(files_result, 'data', [])]

            print(f"✅ 공지사항 저장 완료: {notice_data['title'][:50]}...")
            return result_dict  # 항상 dict 리턴
        except Exception as e:
            # 롤백: 이미 insert된 데이터 삭제
            try:
                if 'notice_id' in locals():
                    self.client.table("schedules").delete().eq("notice_id", notice_id).execute()
                    self.client.table("notice_images").delete().eq("notice_id", notice_id).execute()
                    self.client.table("notice_files").delete().eq("notice_id", notice_id).execute()
                    self.client.table("notice").delete().eq("id", notice_id).execute()
                    print(f"🛑 예외 발생으로 notice_id={notice_id} 관련 데이터 롤백 완료")
            except Exception as rollback_e:
                print(f"❗ 롤백 중 추가 오류 발생: {rollback_e}")
            print(f"❌ 공지사항 저장 실패: {e}")
            raise

    def get_recent_notices(self, limit: int = 10):
        """최근 공지사항 조회"""
        try:
            result = self.client.table("notice")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ 최근 공지사항 조회 실패: {e}")
            raise
