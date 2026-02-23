"""
Модели базы данных для хранения пользователей, событий и уведомлений
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Пользователи бота"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    is_subscribed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User(chat_id={self.chat_id}, username={self.username})>"


class TicketEvent(Base):
    """События (спектакли) с билетами"""
    __tablename__ = 'ticket_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date = Column(DateTime, nullable=True)       # Дата спектакля
    venue = Column(String(500), nullable=True)         # Площадка
    source = Column(String(100), nullable=False)       # shalom_site, afisha, mosbilet
    url = Column(Text, nullable=False)                 # Прямая ссылка на покупку
    status = Column(String(50), default='available')   # available, sold_out, monitoring
    notified = Column(Boolean, default=False)          # Отправлено ли уведомление
    discovered_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TicketEvent(date={self.event_date}, source={self.source}, status={self.status})>"


class NotificationLog(Base):
    """Лог отправленных уведомлений"""
    __tablename__ = 'notification_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=True)              # ID события из TicketEvent
    notification_type = Column(String(50), nullable=False) # new_sale, returned_tickets, announcement
    message = Column(Text, nullable=False)                 # Текст отправленного сообщения
    recipients_count = Column(Integer, default=0)          # Сколько пользователей получили
    sent_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_text = Column(Text, nullable=True)               # Текст ошибки, если success=False

    def __repr__(self):
        return f"<NotificationLog(type={self.notification_type}, sent_at={self.sent_at}, success={self.success})>"


class MonitoringState(Base):
    """Состояние мониторинга (для отслеживания режимов)"""
    __tablename__ = 'monitoring_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), unique=True, nullable=False)  # shalom_site, afisha, etc.
    last_check = Column(DateTime, default=datetime.utcnow)
    last_success = Column(DateTime, nullable=True)
    mode = Column(String(20), default='normal')  # normal, enhanced
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    def __repr__(self):
        return f"<MonitoringState(source={self.source}, mode={self.mode})>"
