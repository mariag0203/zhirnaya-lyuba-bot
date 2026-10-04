"""
Офлайн-проверка логики монитора: ответы сайта подменяются, в сеть ничего не уходит.
Запуск из папки бота:  python -m unittest tests.test_mosbilet -v
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

_tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ['BOT_TOKEN'] = '123:test'
os.environ['ADMIN_CHAT_ID'] = '1'
os.environ['NOTIFY_COOLDOWN_MIN'] = '10'
os.environ['PARSE_ALERT_AFTER'] = '3'

from sqlalchemy import update  # noqa: E402

from database import init_db  # noqa: E402
from database.db import async_session_maker  # noqa: E402
from database.models import Show, User  # noqa: E402
from monitors.base_monitor import RequestError  # noqa: E402
from monitors.mosbilet import MosbiletMonitor, ParseError  # noqa: E402
from bot import handlers  # noqa: E402

A = datetime(2027, 3, 10, 19, 0)
B = datetime(2027, 3, 24, 19, 0)


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kw):
        self.sent.append((chat_id, text))


class FakeSite:
    """Подменяет MosbiletMonitor.get_json."""
    def __init__(self):
        self.occurrences = [A]
        self.perf = {}            # datetime -> (free, price)
        self.perf_error = None
        self.broken = False
        self.flag = 0

    async def __call__(self, url, params=None):
        if url.endswith('/occurrences'):
            if self.broken:
                return {'something': 'else'}
            return {'items': [{'date_from': d.strftime('%Y-%m-%d %H:%M:%S')} for d in self.occurrences]}
        if '/afisha/' in url:
            return {'id': 381336257, 'title': 'Жирная Люба', 'ebs_id': 96298, 'ebs_agent_uid': 'museum171',
                    'ebs_has_available_seats': self.flag, 'ebs_opening_date': '2026-09-21 15:00:00'}
        if '/performances' in url:
            if self.perf_error:
                raise RequestError(self.perf_error)
            days = {}
            for d, (free, price) in sorted(self.perf.items()):
                days.setdefault(d.date().isoformat(), []).append({
                    'id': 555, 'start_datetime': d.strftime('%Y-%m-%dT%H:%M:%S'),
                    'free_seats_count': free, 'min_performance_price': price})
            return [{'date': k, 'performances': v} for k, v in days.items()]
        raise AssertionError(url)


class MonitorTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()
        async with async_session_maker() as s:
            if not (await s.get(User, 1)):
                s.add(User(id=1, chat_id=42, first_name='Подписчик', is_subscribed=True))
                await s.commit()
        self.bot = FakeBot()
        self.site = FakeSite()
        self.mon = MosbiletMonitor(bot=self.bot)
        self.mon.get_json = self.site
        await self.mon.initialize()

    def texts(self, chat=42):
        out = [t for c, t in self.bot.sent if c == chat]
        self.bot.sent.clear()
        return out

    async def test_flow(self):
        # 1. первый запуск: показ записан молча, администратору — сводка
        await self.mon.check()
        self.assertTrue(any('Начинаю следить' in t for c, t in self.bot.sent if c == 1))
        self.assertEqual(self.texts(42), [])

        # 2. появился новый показ B
        self.site.occurrences = [A, B]
        await self.mon.check()
        msgs = self.texts()
        self.assertEqual(len(msgs), 1)
        self.assertIn('Новый показ', msgs[0])
        self.assertIn('24.03 (ср), 19:00', msgs[0])
        self.assertIn('https://bilet.mos.ru/event/381336257/', msgs[0])

        # 3. на A появились места
        self.site.perf = {A: (5, 2000)}
        self.site.flag = 1
        await self.mon.check()
        msgs = self.texts()
        self.assertEqual(msgs and msgs[0].splitlines()[0], '🎫 10.03 (ср), 19:00 — появилось 5 мест, от 2000 ₽')

        # 4. места ушли и вернулись в пределах 10 минут — без повтора
        self.site.perf = {}
        await self.mon.check()
        self.site.perf = {A: (1, 3000)}
        await self.mon.check()
        self.assertEqual(self.texts(), [])

        # ... а через 10 минут — снова уведомление
        async with async_session_maker() as s:
            await s.execute(update(Show).values(last_seats_notified_at=datetime.utcnow() - timedelta(minutes=11)))
            await s.commit()
        self.site.perf = {}
        await self.mon.check()
        self.site.perf = {A: (2, 3000)}
        await self.mon.check()
        msgs = self.texts()
        self.assertEqual(len(msgs), 1)
        self.assertIn('появилось 2 места', msgs[0])

        # 5. билетная система недоступна: состояние мест не трогаем, новые показы видим
        self.site.perf_error = 'HTTP 503'
        C = datetime(2027, 4, 7, 19, 0)
        self.site.occurrences = [A, B, C]
        await self.mon.check()
        msgs = self.texts()
        self.assertEqual(len(msgs), 1)
        self.assertIn('07.04 (ср), 19:00', msgs[0])
        self.assertIs(self.mon.health.seats_source_ok, False)
        self.site.perf_error = None

        # 6. /status: московское время, показы, места
        answers = []

        async def answer(text, **kw):
            answers.append(text)
        handlers.MONITOR['mosbilet'] = self.mon
        msg = SimpleNamespace(chat=SimpleNamespace(id=42), answer=answer)
        await self.mon.check()
        self.texts()
        await handlers.cmd_status(msg)
        st = answers[0]
        self.assertIn('Найдено показов: 3, свободных мест всего: 2', st)
        self.assertIn('10.03 (ср), 19:00 — 2 места, от 3000 ₽', st)
        self.assertIn('(МСК)', st)

        # 7. сайт перестал отдавать показы — после 3 пустых проверок пишет администратору, один раз
        self.site.occurrences = []
        for _ in range(4):
            await self.mon.check()
        admin = [t for c, t in self.bot.sent if c == 1]
        self.assertEqual(sum('ничего не видит' in t for t in admin), 1)
        self.bot.sent.clear()

        # поломанный формат ответа — это ParseError и тоже «пусто»
        self.site.broken = True
        with self.assertRaises(ParseError):
            await self.mon.check()
        self.assertEqual(self.mon.health.consecutive_empty, 5)

        # восстановление
        self.site.broken = False
        self.site.occurrences = [A, B, C]
        await self.mon.check()
        self.assertTrue(any('снова находятся' in t for c, t in self.bot.sent if c == 1))

        # 8. ежедневный отчёт
        from utils.scheduler import MonitorScheduler
        sch = MonitorScheduler()
        sch.monitor = self.mon
        self.assertIn('Я работаю', sch.heartbeat_text())
        # один сбой билетной системы — не проблема; пять подряд — проблема
        self.mon.health.consecutive_seats_failures = 1
        self.assertNotIn('Сейчас есть проблема', sch.heartbeat_text())
        self.mon.health.consecutive_seats_failures = 5
        self.assertIn('билетная система не отвечает', sch.heartbeat_text())



class SendRetryTest(unittest.IsolatedAsyncioTestCase):
    async def test_retry_then_ok(self):
        from aiogram.exceptions import TelegramNetworkError
        from bot import notifications
        notifications.SEND_RETRY_DELAYS = (0, 0, 0)

        class FlakyBot:
            calls = 0

            async def send_message(self, **kw):
                FlakyBot.calls += 1
                if FlakyBot.calls < 3:
                    raise TelegramNetworkError(method=None, message='Request timeout error')

        await notifications.send_with_retry(FlakyBot(), 1, 'x')
        self.assertEqual(FlakyBot.calls, 3)

        class DeadBot:
            async def send_message(self, **kw):
                raise TelegramNetworkError(method=None, message='Request timeout error')
        with self.assertRaises(TelegramNetworkError):
            await notifications.send_with_retry(DeadBot(), 1, 'x')


if __name__ == '__main__':
    unittest.main()
