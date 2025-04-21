import json
import os
import asyncio
import csv
from typing import Any, Dict, List, Optional
from iexchange_client import IExchangeClient

class MockExchangeClient(IExchangeClient):
    """
    回测用虚拟交易所，支持历史K线回放、虚拟账户、订单撮合等。
    """
    def __init__(self, kline_path: str, initial_balance: Dict[str, float] = None, fee_rate: float = 0.001, slippage: float = 0.0, symbol: str = 'BNB/USDT'):
        self.kline_path = kline_path
        self.kline_data = self._load_kline_data()
        self.kline_index = 0
        self.orders = []  # 活跃订单
        self.trades = []  # 成交记录
        self.balance = initial_balance or {'USDT': 10000.0, 'BNB': 0.0}
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.order_id_counter = 1
        self.markets_loaded = True
        self.time_diff = 0
        self.symbol = symbol
        # 自动解析base/quote币种
        if '/' in symbol:
            self.base, self.quote = symbol.split('/')
        else:
            self.base, self.quote = 'BNB', 'USDT'
        self._sync_base_quote()

    def _load_kline_data(self) -> List[List[Any]]:
        if not os.path.exists(self.kline_path):
            raise FileNotFoundError(f"K线数据文件不存在: {self.kline_path}")
        with open(self.kline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: Optional[int] = None) -> List[List[Any]]:
        # 支持日线聚合
        if timeframe.lower() in ['1d', 'd1', 'day', 'daily']:
            # 聚合所有1小时K线为日线K线
            from collections import defaultdict
            import datetime
            daily = defaultdict(list)
            for k in self.kline_data:
                # k[0]为毫秒时间戳，转为UTC日期
                dt = datetime.datetime.utcfromtimestamp(k[0] // 1000)
                day_key = dt.date()
                daily[day_key].append(k)
            # 按日期排序
            days = sorted(daily.keys())
            daily_klines = []
            for day in days:
                ks = daily[day]
                open_ = ks[0][1]
                high_ = max(x[2] for x in ks)
                low_ = min(x[3] for x in ks)
                close_ = ks[-1][4]
                # 日线时间戳为该日零点（毫秒）
                ts = int(datetime.datetime.combine(day, datetime.time(0,0)).timestamp() * 1000)
                daily_klines.append([ts, open_, high_, low_, close_])
            if limit is not None:
                daily_klines = daily_klines[-limit:]
            return daily_klines
        # 原有1小时K线逻辑
        if limit is None:
            limit = 100
        start = max(0, self.kline_index - limit + 1)
        return self.kline_data[start:self.kline_index+1]

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        # 返回当前K线的收盘价
        k = self.kline_data[self.kline_index]
        return {'last': k[4], 'close': k[4], 'open': k[1], 'high': k[2], 'low': k[3], 'timestamp': k[0]}

    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        # 仅支持限价单，立即撮合
        k = self.kline_data[self.kline_index]
        exec_price = price if price is not None else k[4]
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
        self._sync_base_quote()
        # 记录成交
        trade = {
            'timestamp': k[0],
            'side': side,
            'price': exec_price,
            'amount': amount,
            'cost': amount * exec_price,
            'fee': fee,
            'order_id': order_id,
            'profit': 0  # 回测可后续补充
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
        result = {
            'free': self.balance.copy(),
            'used': {'USDT': 0, 'BNB': 0},
            'total': self.balance.copy()
        }
        # 兼容主流程对'balance[base]'和'balance[quote]'的访问
        result['free']['base'] = self.balance.get(self.base, 0)
        result['free']['quote'] = self.balance.get(self.quote, 0)
        result['total']['base'] = self.balance.get(self.base, 0)
        result['total']['quote'] = self.balance.get(self.quote, 0)
        self._sync_base_quote()
        return result

    async def fetch_my_trades(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.trades[-limit:]

    async def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        # 用当前K线的收盘价模拟盘口
        k = self.kline_data[self.kline_index]
        price = k[4]
        return {
            'asks': [[price * 1.001, 100]],
            'bids': [[price * 0.999, 100]]
        }

    async def close(self):
        pass

    # 回测推进：手动推进K线
    async def next(self):
        if self.kline_index < len(self.kline_data) - 1:
            self.kline_index += 1
            await asyncio.sleep(0)  # 兼容异步
        else:
            raise StopIteration('回测已到末尾')

    def export_trades_to_csv(self, file_path: str):
        if not self.trades:
            return False
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'side', 'price', 'amount', 'cost', 'fee', 'order_id', 'profit'])
            writer.writeheader()
            for trade in self.trades:
                writer.writerow(trade)
        return True

    def export_trades_to_json(self, file_path: str):
        if not self.trades:
            return False
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.trades, f, ensure_ascii=False, indent=2)
        return True

    def export_equity_curve_to_csv(self, file_path: str):
        # 简单实现：按成交顺序统计总资产（USDT+BNB*当前成交价）
        equity = []
        usdt = self.balance.get('USDT', 0)
        bnb = self.balance.get('BNB', 0)
        for trade in self.trades:
            if trade['side'] == 'buy':
                usdt -= trade['cost'] + trade['fee']
                bnb += trade['amount']
            else:
                bnb -= trade['amount']
                usdt += trade['cost'] - trade['fee']
            total = usdt + bnb * trade['price']
            equity.append({'timestamp': trade['timestamp'], 'equity': total})
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'equity'])
            writer.writeheader()
            for row in equity:
                writer.writerow(row)
        return True

    async def fetch_funding_balance(self):
        # 回测模式下无理财账户，返回空结构
        return {}

    @property
    def exchange(self):
        # mock一个带market方法的对象，自动解析base/quote
        class Dummy:
            def market(self, symbol):
                if '/' in symbol:
                    base, quote = symbol.split('/')
                else:
                    base, quote = 'BNB', 'USDT'
                return {'symbol': symbol, 'base': base, 'quote': quote}
        return Dummy()

    def _sync_base_quote(self):
        self.balance['base'] = self.balance.get(self.base, 0)
        self.balance['quote'] = self.balance.get(self.quote, 0) 