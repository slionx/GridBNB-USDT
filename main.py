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
    return parser.parse_args()

async def main():
    args = parse_args()
    # 优先命令行，其次环境变量，最后默认
    mode = args.mode or os.getenv('TRADING_MODE', 'live')
    mode = mode.lower()
    initial_balance = None
    if args.init_usdt is not None or args.init_bnb is not None:
        initial_balance = {
            'USDT': args.init_usdt if args.init_usdt is not None else 10000.0,
            'BNB': args.init_bnb if args.init_bnb is not None else 0.0
        }
    # 选择交易所实现
    if mode == 'backtest':
        kline_path = args.kline or os.getenv('BACKTEST_KLINE_PATH')
        if not kline_path:
            print('回测模式需指定K线数据文件路径 --kline')
            sys.exit(1)
        exchange: IExchangeClient = MockExchangeClient(kline_path, initial_balance=initial_balance)
        print('已启用回测模式')
    elif mode == 'simulate':
        exchange: IExchangeClient = SimulateExchangeClient(initial_balance=initial_balance)
        print('已启用模拟盘模式')
    else:
        exchange: IExchangeClient = ExchangeClient()
        print('已启用实盘模式')
    config = TradingConfig()
    
    try:
        # 初始化统一日志配置
        LogConfig.setup_logger()
        logging.info("="*50)
        logging.info("网格交易系统启动")
        logging.info("="*50)
        
        # 使用正确的参数初始化交易器
        trader = GridTrader(exchange, config)
        
        # 初始化交易器
        await trader.initialize()
        
        # 启动Web服务器
        web_server_task = asyncio.create_task(start_web_server(trader))
        
        # 启动交易循环
        trading_task = asyncio.create_task(trader.main_loop())
        
        # 等待所有任务完成
        await asyncio.gather(web_server_task, trading_task)
        
    except Exception as e:
        error_msg = f"启动失败: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        send_pushplus_message(error_msg, "致命错误")
        
    finally:
        if 'trader' in locals():
            try:
                await trader.exchange.close()
                logging.info("交易所连接已关闭")
            except Exception as e:
                logging.error(f"关闭连接时发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 