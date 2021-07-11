from abc import ABC, abstractmethod


class Grabber(ABC):
    @abstractmethod
    def get_response(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_exchange_rate(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_exchange_rates(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _get_base_currency_code(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _get_destination_currency_code(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _get_buy_rate(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _get_sale_rate(self, *args, **kwargs):
        raise NotImplementedError
