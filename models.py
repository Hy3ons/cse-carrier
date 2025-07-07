from sqlalchemy import Column, Integer, String, Text, Boolean, Date, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Notice(Base):
    __tablename__ = 'notice'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text)
    writer = Column(String(100))
    writer_email = Column(String(100))
    publish_date = Column(Date)
    is_notice = Column(Boolean, default=False, index=True)
    ai_summary_title = Column(Text)
    ai_summary_content = Column(Text)
    markdown_content = Column(Text)
    original_url = Column(Text, unique=True)
    ignore_flag = Column(Boolean, default=False)
    title_hash = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    category = Column(Integer, nullable=False, index=True)
    
    # OneToMany 관계
    images = relationship('NoticeImage', back_populates='notice', cascade='all, delete-orphan')
    files = relationship('NoticeFile', back_populates='notice', cascade='all, delete-orphan')
    schedules = relationship('Schedule', back_populates='notice', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Notice(id={self.id}, title='{self.title[:30]}...')>"

class NoticeImage(Base):
    __tablename__ = 'notice_images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    
    notice_id = Column(Integer, ForeignKey('notice.id', ondelete='CASCADE'))

    # ManyToOne 관계 설정
    notice = relationship('Notice', back_populates='images')

    def __repr__(self):
        return f"<NoticeImage(id={self.id}, url='{self.url[:50]}...')>"

class NoticeFile(Base):
    __tablename__ = 'notice_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(300), nullable=False)
    url = Column(Text, nullable=False)

    notice_id = Column(Integer, ForeignKey('notice.id', ondelete='CASCADE'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ManyToOne 관계 설정
    notice = relationship('Notice', back_populates='files')

    def __repr__(self):
        return f"<NoticeFile(id={self.id}, filename='{self.filename}')>"

class Schedule(Base):
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(250))
    description = Column(Text)
    begin = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), index=True, nullable=False)
    is_ignored = Column(Boolean, default=False, nullable=False)
    
    notice_id = Column(Integer, ForeignKey('notice.id', ondelete='CASCADE'))

    notice = relationship('Notice', back_populates='schedules')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Schedule(id={self.id}, title='{self.title}')>"

class Webhook(Base):
    __tablename__ = 'webhooks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Webhook(id={self.id}, name='{self.name}', url='{self.url[:50]}...')>"