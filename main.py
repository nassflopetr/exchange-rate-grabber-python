import os, time
import pickle
import logging
import requests
from redis import Redis
from typing import Union
from dotenv import load_dotenv
from threading import Thread, Lock
from grabber import Grabber
from nbu import NBUGrabber
from oschadbank import OschadBankGrabber
from privatbank import PrivatBankGrabber
from ukrgasbank import UkrGasBankGrabber
from ukrsibbank import UkrSibBankGrabber
from exception import ExchangeRateGrabberException
from model import ExchangeRate, ExchangeRateObserver


load_dotenv('./.env')

os.environ['TZ'] = os.getenv('GRABBER_TIMEZONE')

time.tzset()

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(os.getenv('GRABBER_LOG_FILE_PATH'))
formatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

try:
    _GRABBERS = {
        NBUGrabber.__name__: {'class': NBUGrabber, 'name': 'Національний банк України'},
        OschadBankGrabber.__name__: {'class': OschadBankGrabber, 'name': 'ОщадБанк'},
        PrivatBankGrabber.__name__: {'class': PrivatBankGrabber, 'name': 'ПриватБанк'},
        UkrGasBankGrabber.__name__: {'class': UkrGasBankGrabber, 'name': 'УКРГАЗБАНК'},
        UkrSibBankGrabber.__name__: {'class': UkrSibBankGrabber, 'name': 'УкрСибБанк'},
    }

    _CURRENCY_CODES = (
        {'base_currency_code': 'UAH', 'destination_currency_code': 'USD'},
        {'base_currency_code': 'UAH', 'destination_currency_code': 'EUR'},
    )

    redis = Redis(
        host=os.getenv('GRABBER_REDIS_HOST'),
        port=os.getenv('GRABBER_REDIS_PORT'),
        password=os.getenv('GRABBER_REDIS_PASSWORD')
    )

    class ExchangeRateNotifyObserver(ExchangeRateObserver):
        def exchange_rate_created(self, exchange_rate: ExchangeRate) -> None:
            self._send_notify(None, exchange_rate)

        def exchange_rate_updated(self, pre_exchange_rate: ExchangeRate, latest_exchange_rate: ExchangeRate) -> None:
            # self._send_notify(pre_exchange_rate, latest_exchange_rate)
            pass

        def exchange_rate_changed(self, pre_exchange_rate: ExchangeRate, latest_exchange_rate: ExchangeRate) -> None:
            self._send_notify(pre_exchange_rate, latest_exchange_rate)

        def _send_notify(
                self,
                pre_exchange_rate: Union[ExchangeRate, None],
                latest_exchange_rate: ExchangeRate
        ) -> None:
            global logger

            response = requests.post(
                f'https://api.telegram.org/bot{os.getenv("GRABBER_TELEGRAM_TOKEN")}/sendMessage',
                params={
                    'chat_id': os.getenv('GRABBER_TELEGRAM_CHAT_ID'),
                    'text': self._get_notify_message(pre_exchange_rate, latest_exchange_rate),
                    'parse_mode': 'HTML'
                },
                timeout=30
            )

            if response.status_code != requests.codes.ok:
                raise Exception(
                    f'Open {response.url} stream failed. Response code {response.status_code}.'
                )

            logger.info(f'Telegram success sent the message. {response.text}')

        def _get_notify_message(
                self,
                pre_exchange_rate: Union[ExchangeRate, None],
                latest_exchange_rate: ExchangeRate
        ) -> str:
            global _GRABBERS

            grabber_name = _GRABBERS[latest_exchange_rate.get_grabber().__class__.__name__]['name']
            exchanged_at = latest_exchange_rate.get_timestamp().strftime('%d.%m.%Y %H:%M:%S')

            if pre_exchange_rate is not None:
                buy_rate_changed_at = latest_exchange_rate.get_buy_rate() - pre_exchange_rate.get_buy_rate()
                sale_rate_changed_at = latest_exchange_rate.get_sale_rate() - pre_exchange_rate.get_sale_rate()
            else:
                buy_rate_changed_at = 0
                sale_rate_changed_at = 0

            base_currency_code = latest_exchange_rate.get_base_currency_code()
            destination_currency_code = latest_exchange_rate.get_destination_currency_code()
            buy_exchange_rate_formatted = '{0:,.2f}'.format(latest_exchange_rate.get_buy_rate())
            sale_exchange_rate_formatted = '{0:,.2f}'.format(latest_exchange_rate.get_sale_rate())

            if buy_rate_changed_at != 0:
                buy_rate_changed_at_formatted = ' ({0:+.2f})'.format(buy_rate_changed_at)
            else:
                buy_rate_changed_at_formatted = ''

            if sale_rate_changed_at != 0:
                sale_rate_changed_at_formatted = ' ({0:+.2f})'.format(sale_rate_changed_at)
            else:
                sale_rate_changed_at_formatted = ''

            return f'{grabber_name} \n' \
                   f'\n' \
                   f'Обмін на:\n' \
                   f'<b>{exchanged_at}</b>\n' \
                   f'Купівля:\n' \
                   f'<b>1 {destination_currency_code} -&gt; {buy_exchange_rate_formatted}' \
                   f'{buy_rate_changed_at_formatted} {base_currency_code}</b>\n' \
                   f'Продаж:\n' \
                   f'<b>1 {destination_currency_code} -&gt; {sale_exchange_rate_formatted}' \
                   f'{sale_rate_changed_at_formatted} {base_currency_code}</b>'

    def operate_grabber(grabber: Grabber, lock: Lock) -> None:
        global _CURRENCY_CODES, logger, redis

        try:
            response = grabber.get_response()

            for currency_code in _CURRENCY_CODES:
                exchange_rate = grabber.get_exchange_rate(
                    currency_code['base_currency_code'],
                    currency_code['destination_currency_code'],
                    response
                )

                if exchange_rate is None:
                    logger.warning(
                        f'{grabber.__class__.__name__} exchange rate for {currency_code["base_currency_code"]} -> '
                        f'{currency_code["destination_currency_code"]} was not found.'
                    )

                    continue

                exchange_rate_redis_key = \
                    f"{grabber.__class__.__name__}:" \
                    f"{currency_code['base_currency_code']}:" \
                    f"{currency_code['destination_currency_code']}"

                lock.acquire()

                if redis.exists(exchange_rate_redis_key):
                    pre_exchange_rate = pickle.loads(redis.get(exchange_rate_redis_key))

                    pre_exchange_rate.update_exchange_rate(
                        exchange_rate.get_buy_rate(),
                        exchange_rate.get_sale_rate(),
                        exchange_rate.get_timestamp()
                    )

                    redis.set(exchange_rate_redis_key, pickle.dumps(pre_exchange_rate))
                else:
                    exchange_rate.attach(ExchangeRateNotifyObserver())

                    exchange_rate.notify_exchange_rate_created()

                    redis.set(exchange_rate_redis_key, pickle.dumps(exchange_rate))

                lock.release()
        except ExchangeRateGrabberException as e:
            logger.error(e, exc_info=True)

        except Exception as e:
            logger.critical(e, exc_info=True)

    threads = []

    lock = Lock()

    for grabber_class_name in _GRABBERS:
        thread = Thread(target=operate_grabber, args=(_GRABBERS[grabber_class_name]['class'](), lock,))

        threads.append(thread)

        thread.start()

    for thread in threads:
        thread.join()

except Exception as e:
    logger.critical(e, exc_info=True)
