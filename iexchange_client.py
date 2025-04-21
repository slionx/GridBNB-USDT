from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class IExchangeClient(ABC):
    """
    统一交易所接口协议，所有交易所客户端（实盘、回测、模拟盘）均需实现。
    """

    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: Optional[int] = None) -> List[List[Any]]:
        """
        获取K线数据。
        :param symbol: 交易对，如 'BNB/USDT'
        :param timeframe: K线周期，如 '1h', '4h'
        :param limit: 返回条数
        :return: K线数据列表
        """
        pass

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取最新行情。
        :param symbol: 交易对
        :return: 行情字典
        """
        pass

    @abstractmethod
    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """
        创建订单。
        :param symbol: 交易对
        :param type: 订单类型（'limit'/'market'等）
        :param side: 'buy' 或 'sell'
        :param amount: 数量
        :param price: 价格（市价单可为None）
        :return: 订单信息
        """
        pass

    @abstractmethod
    async def fetch_balance(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取账户余额。
        :param params: 额外参数
        :return: 余额信息
        """
        pass

    @abstractmethod
    async def fetch_my_trades(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取历史成交记录。
        :param symbol: 交易对
        :param limit: 返回条数
        :return: 成交记录列表
        """
        pass

    @abstractmethod
    async def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """
        获取订单簿数据。
        :param symbol: 交易对
        :param limit: 档位数
        :return: 订单簿字典
        """
        pass

    @abstractmethod
    async def close(self):
        """
        关闭连接，释放资源。
        """
        pass 