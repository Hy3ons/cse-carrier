from typing import cast
from bs4 import BeautifulSoup, Tag


class Board:
    def __init__ (self, boardHtml : str, baseUrl : str) :
        soup = BeautifulSoup(boardHtml, 'html.parser')

        tbody = soup.select_one('tbody')

        assert tbody is not None

        # 게시글 제목 (첫 번째 행)
        title_tag = tbody.select_one('td.b-title-box')
        assert title_tag is not None, "title Tag가 없습니다."

        self.title = title_tag.get_text(strip=True)

        # 작성자 (두 번째 행)
        writer_tag = tbody.select_one('tr:nth-of-type(2) td.b-no-right')
        assert writer_tag is not None, "writer Tag가 없습니다."

        self.writer = writer_tag.get_text(strip=True)

        # 조회수 (세 번째 행, 첫 번째 td)
        views_tag = tbody.select_one('tr:nth-of-type(3) td')
        assert views_tag is not None, "views Tag가 없습니다."

        self.views = views_tag.get_text(strip=True)

        # 등록일 (세 번째 행, 마지막 td)
        date_tag = tbody.select_one('tr:nth-of-type(3) td.b-no-right')
        assert date_tag is not None, "date Tag가 없습니다."

        self.date = date_tag.get_text(strip=True)

        # 이메일 (네 번째 행)
        email_tag = tbody.select_one('tr:nth-of-type(4) td.b-no-right')
        assert email_tag is not None, "email Tag가 없습니다."

        self.email = email_tag.get_text(strip=True)

        # 상세 내용 (div.fr-view 내부)
        detail_div = tbody.select_one('div.fr-view')
        assert isinstance(detail_div, Tag)

        self.detail_text = detail_div.get_text(separator='\n', strip=True) if detail_div else ''

        self.images = []
        CNU_URL = 'https://computer.cnu.ac.kr'

        if detail_div:
            img_tags: list[Tag] = cast(list[Tag], detail_div.find_all('img'))

            for img in img_tags:
                url: str = cast(str, img.get('src'))

                if url.startswith('http'):
                    self.images.append(url)
                else:
                    self.images.append(CNU_URL + url)

        self.file_box = []
        file_box = soup.select_one('div.b-file-box')

        if file_box:
            for li in file_box.select('ul li'):
                # 다운로드 링크와 파일명 추출
                download_a = li.select_one('a.file-down-btn.pdf')
                download_a2 = li.select_one('a.file-down-btn.hwp')
                download_a3 = li.select_one('a.file-down-btn.zip')

                if download_a:
                    self.file_box.append({
                        'file_name': download_a.get_text(strip=True),
                        'download_link': baseUrl + cast(str, download_a.get('href'))
                    })

                if download_a2:
                    self.file_box.append({
                        'file_name': download_a2.get_text(strip=True),
                        'download_link': baseUrl + cast(str, download_a2.get('href'))
                    })

                if download_a3:
                    self.file_box.append({
                        'file_name': download_a3.get_text(strip=True),
                        'download_link': baseUrl + cast(str, download_a3.get('href'))
                    })

