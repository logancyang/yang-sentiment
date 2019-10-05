import requests
from settings import CRYPTOCOMPARE_API_KEY


def _join_symbols_by_comma(symbols):
    return ",".join(symbols)


class CryptocompareClient:
    def __init__(self, cryptos=['BTC', 'ADA']):
        """Initialize client for Cryptocompare API

        Arguments:
            cryptos {list} -- A list of strings, each is a symbol such as
            'BTC', 'ADA', 'ETH', etc.
        """
        self.url = (f"https://min-api.cryptocompare.com/data/pricemulti?"
                         f"fsyms={_join_symbols_by_comma(cryptos)}&tsyms=USD")
        self.api_key = CRYPTOCOMPARE_API_KEY

    def get_prices(self):
        headers = {'authorization': f"Apikey {self.api_key}"}
        # Example response: {'BTC': {'USD': 10418.83}, 'ADA': {'USD': 0.05811}}
        return requests.get(self.url, headers=headers).json()
