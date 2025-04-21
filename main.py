import asyncio
import logging
import traceback
import platform
import sys
import os
import argparse
from trader import GridTrader
from helpers import LogConfig, send_pushplus_message
from web_server import start_web_server
from exchange_client import ExchangeClient
from mock_exchange_client import MockExchangeClient
from simulate_exchange_client import SimulateExchangeClient
from iexchange_client import IExchangeClient
from config import TradingConfig

# 在Windows平台上设置SelectorEventLoop
if platform.system() == 'Windows':
    import asyncio
    # 在Windows平台上强制使用SelectorEventLoop
    if sys.version_info[0] == 3 and sys.version_info[1] >= 8:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logging.info("已设置Windows SelectorEventLoop策略")

def parse_args():
    parser = argparse.ArgumentParser(description='GridBNB-USDT 启动参数')
    parser.add_argument('--mode', type=str, default=None, help='运行模式: live/simulate/backtest')
    parser.add_argument('--kline', type=str, default=None, help='回测K线数据文件路径')
    parser.add_argument('--init-usdt', type=float, default=None, help='初始USDT资金')
    parser.add_argument('--init-bnb', type=float, default=None, help='初始BNB资金')
    parser.add_argument('--fast-backtest', action='store_true', help='极速回测模式（不启动Web/日志，仅输出总盈亏）')
    return parser.parse_args()

async def main():
    args = parse_args()
    mode = args.mode or os.getenv('TRADING_MODE', 'live')
    mode = mode.lower()
    initial_balance = None
    if args.init_usdt is not None or args.init_bnb is not None:
        initial_balance = {
            'USDT': args.init_usdt if args.init_usdt is not None else 10000.0,
            'BNB': args.init_bnb if args.init_bnb is not None else 0.0
        }
    # 极速回测模式：日志级别ERROR，不启动Web
    fast_backtest = getattr(args, 'fast_backtest', False)
    if fast_backtest:
        logging.basicConfig(level=logging.ERROR)
    # 选择交易所实现
    if mode == 'backtest':
        kline_path = args.kline or os.getenv('BACKTEST_KLINE_PATH')
        if not kline_path:
            print('回测模式需指定K线数据文件路径 --kline')
            sys.exit(1)
        exchange = MockExchangeClient(kline_path, initial_balance=initial_balance)
        print('已启用回测模式')
    else:
        print('极速回测仅支持backtest模式')
        sys.exit(1)
    config = TradingConfig()
    trader = GridTrader(exchange, config)
    # 极速回测主循环
    async def fast_backtest_main():
        await trader.initialize()
        kline_len = len(exchange.kline_data)
        try:
            for _ in range(kline_len - 1):  # 每次推进一根K线
                await trader.step_once()
                try:
                    await exchange.next()
                except StopIteration:
                    break
                # 打印总资产（由trader.py主循环内已实现，可选保留此处）
        except Exception as e:
            print(f"主循环异常退出: {e}")
        # 回测结束后输出总盈亏
        balance = await trader.exchange.fetch_balance()
        funding_balance = await trader.exchange.fetch_funding_balance()
        current_price = await trader._get_latest_price()
        usdt = float(balance['total'].get('USDT', 0)) + float(funding_balance.get('USDT', 0))
        bnb = float(balance['total'].get('BNB', 0)) + float(funding_balance.get('BNB', 0))
        total = usdt + bnb * current_price
        initial = config.INITIAL_PRINCIPAL
        profit = total - initial if initial > 0 else 0
        print(f"回测结束，总资产: {total:.2f} USDT，初始本金: {initial:.2f}，总盈亏: {profit:.2f} USDT")
    if fast_backtest:
        await fast_backtest_main()
    else:
        # 原有流程（含Web服务等）
        await asyncio.gather(trader.main_loop(), start_web_server(trader))

if __name__ == "__main__":
    asyncio.run(main()) 