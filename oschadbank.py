import re
import requests
from typing import Union, Iterator
from model import ExchangeRate
from bs4 import BeautifulSoup, element
from exception import ExchangeRateGrabberException
from grabber import Grabber


class OschadBankGrabber(Grabber):
    def get_response(self) -> str:
        try:
            response = requests.get('https://www.oschadbank.ua/ua/private/currency', timeout=30)

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
        for exchange_rate in self.get_exchange_rates(response):
            if (exchange_rate.get_base_currency_code() == base_currency_code
                    and exchange_rate.get_destination_currency_code() == destination_currency_code):
                return exchange_rate

        return None

    def get_exchange_rates(self, response: str = None) -> Iterator[ExchangeRate]:
        if response is None:
            response = self.get_response()

        beautiful_soup = BeautifulSoup(response, 'html.parser')

        trs = beautiful_soup.select('table#currency_date_result > tbody > tr')

        for tr in trs:
            yield ExchangeRate(
                OschadBankGrabber(),
                self._get_base_currency_code(tr),
                self._get_destination_currency_code(tr),
                self._get_buy_rate(tr),
                self._get_sale_rate(tr),
            )

    def _get_base_currency_code(self, tag: element.Tag) -> str:
        return 'UAH'

    def _get_destination_currency_code(self, tag: element.Tag) -> str:
        try:
            td = tag.find_all('td')[0]

            text = td.text.strip()

            if re.search(r'[^A-Z]', text) is not None:
                raise ExchangeRateGrabberException('Invalid value')

            return str(text)

        except IndexError as e:
            raise ExchangeRateGrabberException(e)

    def _get_buy_rate(self, tag: element.Tag) -> float:
        try:
            td = tag.find_all('td')[5]

            text = td.text.strip()

            return float(text)

        except (IndexError, ValueError) as e:
            raise ExchangeRateGrabberException(e)

    def _get_sale_rate(self, tag: element.Tag) -> float:
        try:
            td = tag.find_all('td')[6]

            text = td.text.strip()

            return float(text)

        except (IndexError, ValueError) as e:
            raise ExchangeRateGrabberException(e)
