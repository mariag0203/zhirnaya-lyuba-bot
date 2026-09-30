"""
Модели базы данных
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """Подписчики бота"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    is_subscribed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Show(Base):
    """
    Отдельный показ спектакля (дата и время).

    На Мосбилете у спектакля одна страница /event/381336257/, а показы — это
    «occurrences» этого события. Своих страниц у показов нет; в билетной системе
    у показа есть performance_id, но он виден, только пока на показ есть места.
    Поэтому показ опознаётся по дате и времени начала.
    """
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(BigInteger, nullable=False, index=True)       # ID события на bilet.mos.ru
    starts_at = Column(DateTime, nullable=False, index=True)        # время Москвы, как на сайте
    performance_id = Column(BigInteger, nullable=True)              # ID в билетной системе, если был виден
    free_seats = Column(Integer, default=0)                         # свободные места при последней проверке
    min_price = Column(Integer, nullable=True)                      # минимальная цена, ₽
    is_listed = Column(Boolean, default=True)                       # есть ли показ в расписании сейчас
    first_seen_at = Column(DateTime, default=datetime.utcnow)       # UTC
    last_seen_at = Column(DateTime, default=datetime.utcnow)        # UTC
    seats_changed_at = Column(DateTime, nullable=True)              # UTC
    last_seats_notified_at = Column(DateTime, nullable=True)        # UTC


class NotificationLog(Base):
    """Лог рассылок"""
    __tablename__ = 'notification_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=True)              # здесь: id записи Show
    notification_type = Column(String(50), nullable=False) # new_show, seats, admin
    message = Column(Text, nullable=False)
    recipients_count = Column(Integer, default=0)
    sent_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_text = Column(Text, nullable=True)


class MonitoringState(Base):
    """Время последних проверок (для /status после перезапуска)"""
    __tablename__ = 'monitoring_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), unique=True, nullable=False)
    last_check = Column(DateTime, default=datetime.utcnow)
    last_success = Column(DateTime, nullable=True)
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
