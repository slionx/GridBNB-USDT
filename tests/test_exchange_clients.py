import os
import pytest
import tempfile
from mock_exchange_client import MockExchangeClient
from simulate_exchange_client import SimulateExchangeClient
from exchange_client import ExchangeClient

@pytest.fixture
def sample_kline(tmp_path):
    # 生成简单K线数据文件
    kline = [
        [1, 100, 105, 95, 100],
        [2, 100, 110, 99, 108],
        [3, 108, 112, 107, 110],
        [4, 110, 115, 109, 114],
        [5, 114, 120, 113, 119],
    ]
    file = tmp_path / 'kline.json'
    import json
    with open(file, 'w') as f:
        json.dump(kline, f)
    return str(file)

def test_mock_exchange_basic(sample_kline):
    client = MockExchangeClient(sample_kline, initial_balance={'USDT': 1000, 'BNB': 0})
    # 推进到最后一根K线
    for _ in range(4):
        import asyncio
        asyncio.run(client.next())
    # 测试fetch_ohlcv
    ohlcv = asyncio.run(client.fetch_ohlcv('BNB/USDT', '1h', 3))
    assert len(ohlcv) == 3
    # 测试fetch_ticker
    ticker = asyncio.run(client.fetch_ticker('BNB/USDT'))
    assert 'last' in ticker
    # 测试买入
    order = asyncio.run(client.create_order('BNB/USDT', 'limit', 'buy', 1, 119))
    assert order['status'] == 'closed'
    # 测试余额
    balance = asyncio.run(client.fetch_balance())
    assert balance['total']['BNB'] > 0
    # 测试卖出
    order2 = asyncio.run(client.create_order('BNB/USDT', 'limit', 'sell', 1, 119))
    assert order2['status'] == 'closed'
    # 测试成交记录
    trades = asyncio.run(client.fetch_my_trades('BNB/USDT', 2))
    assert len(trades) == 2
    # 测试导出
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'trades.csv')
        json_path = os.path.join(tmpdir, 'trades.json')
        eq_path = os.path.join(tmpdir, 'equity.csv')
        assert client.export_trades_to_csv(csv_path)
        assert client.export_trades_to_json(json_path)
        assert client.export_equity_curve_to_csv(eq_path)

def test_simulate_exchange_basic(monkeypatch):
    # 用monkeypatch屏蔽真实API调用
    class DummyReal:
        async def fetch_ohlcv(self, *a, **k): return [[1,2,3,4,5]]
        async def fetch_ticker(self, *a, **k): return {'last': 100, 'timestamp': 1}
        async def fetch_order_book(self, *a, **k): return {'asks': [[101, 1]], 'bids': [[99, 1]]}
        async def close(self): pass
    monkeypatch.setattr('simulate_exchange_client.ExchangeClient', lambda: DummyReal())
    client = SimulateExchangeClient(initial_balance={'USDT': 1000, 'BNB': 0})
    import asyncio
    # 测试fetch_ohlcv
    ohlcv = asyncio.run(client.fetch_ohlcv('BNB/USDT'))
    assert ohlcv[0][0] == 1
    # 测试买入
    order = asyncio.run(client.create_order('BNB/USDT', 'limit', 'buy', 1, 100))
    assert order['status'] == 'closed'
    # 测试余额
    balance = asyncio.run(client.fetch_balance())
    assert balance['total']['BNB'] > 0
    # 测试卖出
    order2 = asyncio.run(client.create_order('BNB/USDT', 'limit', 'sell', 1, 100))
    assert order2['status'] == 'closed'
    # 测试成交记录
    trades = asyncio.run(client.fetch_my_trades('BNB/USDT', 2))
    assert len(trades) == 2
    # 测试订单簿
    ob = asyncio.run(client.fetch_order_book('BNB/USDT'))
    assert 'asks' in ob and 'bids' in ob
    # 测试关闭
    asyncio.run(client.close()) 