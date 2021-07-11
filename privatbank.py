import re
import requests
import json
from typing import Union, Set
from grabber import Grabber
from model import ExchangeRate
from exception import ExchangeRateGrabberException


class PrivatBankGrabber(Grabber):
    def get_response(self) -> list:
        try:
            response = requests.get(
                'https://api.privatbank.ua/p24api/pubinfo',
                params={
                    'json': '',
                    'exchange': '',
                    'coursid': 5
                },
                timeout=30
            )

            if response.status_code != requests.codes.ok:
                raise ExchangeRateGrabberException(
                    f'Open {response.url} stream failed. Response code {response.status_code}.'
                )

            return response.json()
        except Exception as e:
            raise ExchangeRateGrabberException(e)

    def get_exchange_rate(
        self,
        base_currency_code: str,
        destination_currency_code: str,
        response: list = None
    ) -> Union[ExchangeRate, None]:
        exchange_rates = self.get_exchange_rates(response)

        for exchange_rate in exchange_rates:
            if (exchange_rate.get_base_currency_code() == base_currency_code
                    and exchange_rate.get_destination_currency_code() == destination_currency_code):
                return exchange_rate

        return None

    def get_exchange_rates(self, response: list = None) -> Set[ExchangeRate]:
        if response is None:
            response = self.get_response()

        exchange_rates = set()

        for row in response:
            exchange_rates.add(ExchangeRate(
                PrivatBankGrabber(),
                self._get_base_currency_code(row),
                self._get_destination_currency_code(row),
                self._get_buy_rate(row),
                self._get_sale_rate(row),
            ))

        return exchange_rates

    def _get_base_currency_code(self, row: dict) -> str:
        try:
            currency_code = row['base_ccy']

            if re.search(r'[^A-Z]', currency_code) is not None:
                raise ExchangeRateGrabberException('Invalid value')

            return str(currency_code)

        except IndexError as e:
            raise ExchangeRateGrabberException(e)

    def _get_destination_currency_code(self, row: dict) -> str:
        try:
            currency_code = row['ccy']

            if re.search(r'[^A-Z]', currency_code) is not None:
                raise ExchangeRateGrabberException('Invalid value')

            return str(currency_code)

        except IndexError as e:
            raise ExchangeRateGrabberException(e)

    def _get_buy_rate(self, row: dict) -> float:
        try:
            rate = row['buy']

            return float(rate)

        except (IndexError, ValueError) as e:
            raise ExchangeRateGrabberException(e)

    def _get_sale_rate(self, row: dict) -> float:
        try:
            rate = row['sale']

            return float(rate)

        except (IndexError, ValueError) as e:
            raise ExchangeRateGrabberException(e)
