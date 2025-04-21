import asyncio
from typing import Any, Dict, List, Optional
from iexchange_client import IExchangeClient
from exchange_client import ExchangeClient

class SimulateExchangeClient(IExchangeClient):
    """
    模拟盘交易所，基于实时行情，虚拟账户和撮合，不与真实交易所交互。
    """
    def __init__(self, initial_balance: Dict[str, float] = None, fee_rate: float = 0.001, slippage: float = 0.0):
        self.real_client = ExchangeClient()
        self.balance = initial_balance or {'USDT': 10000.0, 'BNB': 0.0}
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.trades = []
        self.order_id_counter = 1
        self.markets_loaded = True
        self.time_diff = 0

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: Optional[int] = None) -> List[List[Any]]:
        return await self.real_client.fetch_ohlcv(symbol, timeframe, limit)

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return await self.real_client.fetch_ticker(symbol)

    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        ticker = await self.real_client.fetch_ticker(symbol)
        exec_price = price if price is not None else ticker['last']
        if self.slippage > 0:
            exec_price *= (1 + self.slippage) if side == 'buy' else (1 - self.slippage)
        fee = amount * exec_price * self.fee_rate
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        # 账户变动
        if side == 'buy':
            cost = amount * exec_price + fee
            if self.balance['USDT'] < cost:
                raise Exception('USDT余额不足')
            self.balance['USDT'] -= cost
            self.balance['BNB'] += amount
        else:
            if self.balance['BNB'] < amount:
                raise Exception('BNB余额不足')
            self.balance['BNB'] -= amount
            self.balance['USDT'] += amount * exec_price - fee
        # 记录成交
        trade = {
            'timestamp': ticker.get('timestamp', 0),
            'side': side,
            'price': exec_price,
            'amount': amount,
            'cost': amount * exec_price,
            'fee': fee,
            'order_id': order_id,
            'profit': 0
        }
        self.trades.append(trade)
        return {
            'id': order_id,
            'status': 'closed',
            'price': exec_price,
            'filled': amount,
            'side': side
        }

    async def fetch_balance(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            'free': self.balance.copy(),
            'used': {'USDT': 0, 'BNB': 0},
            'total': self.balance.copy()
        }

    async def fetch_my_trades(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.trades[-limit:]

    async def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        return await self.real_client.fetch_order_book(symbol, limit)

    async def close(self):
        await self.real_client.close() 