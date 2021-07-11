import re
import requests
import datetime
from typing import Union, Set
from model import ExchangeRate
from bs4 import BeautifulSoup, element
from exception import ExchangeRateGrabberException
from grabber import Grabber


class NBUGrabber(Grabber):
    def get_response(self) -> str:
        try:
            response = requests.get(
                'https://bank.gov.ua/ua/markets/exchangerates',
                params={
                    'period': 'daily',
                    'date': datetime.date.today().strftime('%d.%m.%Y')
                },
                timeout=30
            )

            if response.status_code != requests.codes.ok:
                raise ExchangeRateGrabberException(
                    f'Open {response.url} stream failed. Response code {response.status_code}.'
                )

            return response.text
        except Exception as e:
            raise ExchangeRateGrabberException(e)

    def get_exchange_rate(
        self,
        base_currency_code: str,
        destination_currency_code: str,
        response: str = None
    ) -> Union[ExchangeRate, None]:
        exchange_rates = self.get_exchange_rates(response)

        for exchange_rate in exchange_rates:
            if (exchange_rate.get_base_currency_code() == base_currency_code
                    and exchange_rate.get_destination_currency_code() == destination_currency_code):
                return exchange_rate

        return None

    def get_exchange_rates(self, response: str = None) -> Set[ExchangeRate]:
        if response is None:
            response = self.get_response()

        beautiful_soup = BeautifulSoup(response, 'html.parser')

        trs = beautiful_soup.select('table#exchangeRates > tbody > tr')

        exchange_rates = set()

        for tr in trs:
            exchange_rates.add(ExchangeRate(
                NBUGrabber(),
                self._get_base_currency_code(tr),
                self._get_destination_currency_code(tr),
                self._get_buy_rate(tr),
                self._get_sale_rate(tr),
            ))

        return exchange_rates

    def _get_base_currency_code(self, tag: element.Tag) -> str:
        return 'UAH'

    def _get_destination_currency_code(self, tag: element.Tag) -> str:
        try:
            td = tag.find_all('td')[1]

            text = td.text.strip()

            if re.search(r'[^A-Z]', text) is not None:
                raise ExchangeRateGrabberException('Invalid value')

            return str(text)

        except IndexError as e:
            raise ExchangeRateGrabberException(e)

    def _get_buy_rate(self, tag: element.Tag) -> float:
        try:
            td = tag.find_all('td')[4]

            text = td.text.strip()

            return float(text.replace(',', '.'))

        except (IndexError, ValueError) as e:
            raise ExchangeRateGrabberException(e)

    def _get_sale_rate(self, tag: element.Tag) -> float:
        return self._get_buy_rate(tag)
