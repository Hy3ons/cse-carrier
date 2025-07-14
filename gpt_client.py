import openai
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr
from typing import List

class NoticeItem(BaseModel):
    '''내용에 대한 제목 요약, 요약된 내용, 마크다운으로 변환된 전체 내용을 제공하세요.'''

    AI_SUMMARY_TITLE : str
    '''핵심 내용을 담은 간결한 제목 (45자 이내)'''

    AI_SUMMARY_CONTENT: str
    '''중요한 내용을 요약 (100자 이내)'''

    MARKDOWN_CONTENT: str
    '''전체 내용을 원본 의미를 유지하며 사용자가 읽기 쉬운 마크다운 형식으로 변환한다. 이모지를 사용해도 됨.'''

class ScheduleItem(BaseModel):
    title : str
    '''일정의 제목 (예: "2024년 2학기 국가장학금 1차 신청")'''

    description: str
    '''일정에 대한 구체적인 설명'''

    begin: str
    '''일정(신청/제출 기간)이 시작하는 날짜와 시간 (KST, 'YYYY-MM-DDTHH:MM:SS+09:00' 형식)'''

    end: str
    '''일정(신청/제출 기간)이 끝나는 날짜와 시간 (KST, 'YYYY-MM-DDTHH:MM:SS+09:00' 형식)'''

class ScheduleList(BaseModel):
    '''ScheduleItem을 리스트로 하는 멤버를 가지는 Wrapper 클래스'''
    items : List[ScheduleItem]


class GPTClient:
    def __init__(self, api_key: str | None = None):
        load_dotenv()

        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key가 필요합니다.")
        
        self.llm = ChatOpenAI(api_key=SecretStr(self.api_key), model="gpt-4o-mini", temperature=0.4, max_completion_tokens=5000)
        self.structedSummaryLLM = self.llm.with_structured_output(NoticeItem)
        self.structedScheduleLLM = self.llm.with_structured_output(ScheduleList)

    def process_notice_content(self, title: str, content: str) -> NoticeItem:
        '''공지사항 내용을 GPT로 처리하여 요약, 제목, 마크다운 생성'''

        prompt = f"""
다음 대학교 공지사항을 분석하여 JSON 형식으로 정리해주세요.

**공지사항 원문:**
- 제목: {title}
- 내용: {content}

**요구사항:**
1. `AI_SUMMARY_TITLE`: 핵심 내용을 담은 간결한 제목 (45자 이내)
2. `AI_SUMMARY_CONTENT`: 중요한 내용을 요약 (100자 이내)
3. `MARKDOWN_CONTENT`: 전체 내용을 원본 의미를 유지하며 사용자가 읽기 쉬운 마크다운 형식으로 변환한다. 이모지를 사용해도 됨.

**응답 형식 (반드시 아래 JSON 형식 스키마를 준수해주세요):**
{{
  "AI_SUMMARY_TITLE": "string",
  "AI_SUMMARY_CONTENT": "string",
  "MARKDOWN_CONTENT": "string"
}}
"""
        try:
            result = self.structedSummaryLLM.invoke(prompt)
            assert isinstance(result, NoticeItem)

            return result
        except Exception as e:
            print(f"❌ 공지 요약 처리 실패: {e}")
            # 실패 시 기본값 반환
            return NoticeItem(
                AI_SUMMARY_TITLE=title[:30],
                AI_SUMMARY_CONTENT=content[:100],
                MARKDOWN_CONTENT=self._simple_markdown_convert(content)
            )

    def _simple_markdown_convert(self, text: str) -> str:
        """텍스트의 줄바꿈을 <br>로 변환하는 간단한 마크다운 변환기"""
        return text.replace('\n', '<br>')

    def extract_schedule_from_notice(self, title: str, content: str) -> list:
        """공지사항 내용에서 일정 정보를 추출하여 JSON으로 반환"""
        prompt = f"""
다음 대학교 공지사항을 분석하여, **학생들이 반드시 확인하고 행동해야 하는 중요한 일정 정보**를 JSON 객체 배열 형식으로 추출해주세요. 마감 기한이 명확한 일정과 상시 진행되는 일정을 모두 포함해주세요.

**추출 대상:**
- **신청/접수 기간:** 장학금 신청, 프로그램 지원, 수강 신청 등 (상시 접수 포함)
- **제출 마감:** 서류 제출, 과제 제출 등
- **등록/납부 기간:** 등록금 납부, 기숙사 신청 등
- **중요한 행동이 필요한 명확한 마감 기한이 있거나 상시 진행되는 모든 일정**

**제외 대상:**
- **단순 행사 안내:** 축제, 특강, 설명회 등 (단, 사전 신청/등록이 필수인 경우는 추출 대상에 포함)
- **정보 제공성 게시물:** 단순 공지, 소식 전달 등

**공지사항 원문:**
- 제목: {title}
- 내용: {content}

**요구사항:**
1.  `title`: 일정의 제목 (예: "2024년 2학기 국가장학금 1차 신청")
2.  `description`: 일정에 대한 구체적인 설명
3.  `begin`: 일정(신청/제출 기간)이 시작하는 날짜와 시간 (KST, 'YYYY-MM-DDTHH:MM:SS+09:00' 형식)
4.  `end`: 일정(신청/제출 기간)이 끝나는 날짜와 시간 (KST, 'YYYY-MM-DDTHH:MM:SS+09:00' 형식)

- **마감 기한(`end` date)이 없는 상시 일정** (예: "상시 접수", "연중 모집")의 경우, `end` 값은 `9999-12-31T23:59:59+09:00` (KST)로 설정해주세요. 이는 '무기한'을 의미합니다.
- **중요한 행동(신청, 제출 등)이 필요하지 않은 단순 정보는 추출하지 마세요.**
- **신청 시작일(`begin` date) 없이 마감 기한만 명시된 경우,** `begin` 값은 `1970-01-01T00:00:00+09:00` 으로 설정해주세요. 이는 '이미 시작되었음'을 의미합니다.
- 원문에 명시된 모든 날짜와 시간은 **한국 표준시(KST, UTC+9)로 간주**하고, 최종 결과도 **KST**로 반환해주세요.
- 시간이 명확하게 명시되지 않은 경우, `begin` 날짜의 시간은 `00:00:00`으로, `end` 날짜의 시간은 `23:59:59`으로 간주해주세요.
- 모든 날짜는 현재 연도를 기준으로 파싱해주세요.
- 추출할 수 있는 해당 유형의 일정이 하나도 없다면, 빈 배열 `[]`을 반환해주세요.

**응답 형식 (반드시 아래 JSON 형식 스키마를 준수해주세요):**
[
  {{
    "title": "string",
    "description": "string",
    "begin": "YYYY-MM-DDTHH:MM:SS+09:00",
    "end": "YYYY-MM-DDTHH:MM:SS+09:00"
  }}
]
"""
        try:
            result = self.structedScheduleLLM.invoke(prompt)
            assert isinstance(result, ScheduleList)

            return result.items
        except Exception as e:
            print(f"❌ 일정 추출 실패: {e}")
            raise e



