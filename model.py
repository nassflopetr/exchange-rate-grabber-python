from __future__ import annotations
import copy
import math
from typing import Set
from grabber import Grabber
from datetime import datetime
from abc import ABC, abstractmethod
from exception import ExchangeRateGrabberException


class ExchangeRate:
    _grabber: Grabber
    _base_currency_code: str
    _destination_currency_code: str
    _buy_rate: float
    _sale_rate: float
    _timestamp: datetime
    _observers: Set[ExchangeRateObserver]

    def __init__(
        self,
        grabber: Grabber,
        base_currency_code: str,
        destination_currency_code: str,
        buy_rate: float = None,
        sale_rate: float = None,
        timestamp: datetime = None,
        observers: Set[ExchangeRateObserver] = None
    ):
        self._grabber = grabber
        self._base_currency_code = str(base_currency_code)
        self._destination_currency_code = str(destination_currency_code)

        if buy_rate is None or sale_rate is None:
            exchange_rate = self._grabber.get_exchange_rate(
                self._base_currency_code, self._destination_currency_code
            )

            buy_rate = exchange_rate.get_buy_rate()
            sale_rate = exchange_rate.get_sale_rate()
            timestamp = exchange_rate.get_timestamp()

        self._set_exchange_rate(buy_rate, sale_rate, timestamp)

        if observers is None:
            self._observers = set()
        else:
            self._observers = observers

    def refresh(self) -> None:
        exchange_rate = self.get_grabber().get_exchange_rate(
            self.get_base_currency_code(),
            self.get_destination_currency_code()
        )

        if exchange_rate is None:
            raise ExchangeRateGrabberException(
                f'Exchange rate for {self.get_base_currency_code()} -> {self.get_destination_currency_code()} '
                f'was not found.'
            )

        self.update_exchange_rate(
            exchange_rate.get_buy_rate(),
            exchange_rate.get_sale_rate(),
            exchange_rate.get_timestamp()
        )

    def update_exchange_rate(
        self,
        buy_rate: float,
        sale_rate: float,
        timestamp: datetime = None
    ) -> None:
        pre_exchange_rate = copy.deepcopy(self)

        self._set_exchange_rate(buy_rate, sale_rate, timestamp)

        self.notify_exchange_rate_updated(pre_exchange_rate)

        if self._is_exchange_rate_changed(pre_exchange_rate):
            self.notify_exchange_rate_changed(pre_exchange_rate)

    def get_grabber(self) -> Grabber:
        return self._grabber

    def get_base_currency_code(self) -> str:
        return str(self._base_currency_code)

    def get_destination_currency_code(self) -> str:
        return str(self._destination_currency_code)

    def get_buy_rate(self) -> float:
        return float(self._buy_rate)

    def get_sale_rate(self) -> float:
        return float(self._sale_rate)

    def get_timestamp(self) -> datetime:
        return self._timestamp

    def attach(self, observer: ExchangeRateObserver) -> None:
        self._observers.add(observer)

    def detach(self, observer: ExchangeRateObserver) -> None:
        try:
            self._observers.remove(observer)
        except KeyError:
            pass

    def notify_exchange_rate_created(self) -> None:
        for observer in self._observers:
            observer.exchange_rate_created(self)

    def notify_exchange_rate_updated(self, pre_exchange_rate: ExchangeRate) -> None:
        for observer in self._observers:
            observer.exchange_rate_updated(pre_exchange_rate, self)

    def notify_exchange_rate_changed(self, pre_exchange_rate: ExchangeRate) -> None:
        for observer in self._observers:
            observer.exchange_rate_changed(pre_exchange_rate, self)

    def _set_exchange_rate(
        self,
        buy_rate: float,
        sale_rate: float,
        timestamp: datetime = None
    ) -> None:
        self._buy_rate = float(buy_rate)
        self._sale_rate = float(sale_rate)

        if isinstance(timestamp, datetime):
            self._timestamp = timestamp
        else:
            self._timestamp = datetime.now()

    def _is_exchange_rate_changed(self, pre_exchange_rate: ExchangeRate) -> bool:
        return (math.isclose(pre_exchange_rate.get_buy_rate(), self.get_buy_rate()) is not True or
                math.isclose(pre_exchange_rate.get_sale_rate(), self.get_sale_rate()) is not True)

    def get_ob(self):
        return self._observers


class ExchangeRateObserver(ABC):
    @abstractmethod
    def exchange_rate_created(self, exchange_rate: ExchangeRate) -> None:
        raise NotImplementedError

    @abstractmethod
    def exchange_rate_updated(self, pre_exchange_rate: ExchangeRate, latest_exchange_rate: ExchangeRate) -> None:
        raise NotImplementedError

    @abstractmethod
    def exchange_rate_changed(self, pre_exchange_rate: ExchangeRate, latest_exchange_rate: ExchangeRate) -> None:
        raise NotImplementedError
