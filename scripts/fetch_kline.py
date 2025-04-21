import ccxt
import json
import time
import argparse
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description='自动拉取币安K线并保存为回测JSON文件')
    parser.add_argument('--symbol', type=str, default='BNB/USDT', help='币对，如BNB/USDT')
    parser.add_argument('--timeframe', type=str, default='1h', help='K线周期，如1h, 4h, 1d')
    parser.add_argument('--since', type=str, default=None, help='起始时间，格式2021-01-01T00:00:00Z')
    parser.add_argument('--end', type=str, default=None, help='结束时间，格式2022-01-01T00:00:00Z')
    parser.add_argument('--output', type=str, default='kline.json', help='输出文件名')
    return parser.parse_args()

def main():
    args = parse_args()
    exchange = ccxt.binance({
        'proxies': {
            'http': 'http://127.0.0.1:7890',   # 替换为你的代理地址
            'https': 'http://127.0.0.1:7890',
        }
    })
    symbol = args.symbol
    timeframe = args.timeframe
    since = int(exchange.parse8601(args.since)) if args.since else int(time.time() - 365*24*3600) * 1000
    end_time = int(exchange.parse8601(args.end)) if args.end else int(time.time() * 1000)
    limit = 1000
    all_ohlcv = []
    print(f"拉取 {symbol} {timeframe} K线: {datetime.utcfromtimestamp(since/1000)} ~ {datetime.utcfromtimestamp(end_time/1000)}")
    while since < end_time:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        except Exception as e:
            print(f"拉取失败: {e}")
            time.sleep(2)
            continue
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        print(f"已拉取至: {datetime.utcfromtimestamp(ohlcv[-1][0]/1000)}，累计{len(all_ohlcv)}条")
        time.sleep(0.5)
    # 转换为MockExchangeClient兼容格式
    json_data = [[x[0], x[1], x[2], x[3], x[4]] for x in all_ohlcv]
    with open(args.output, 'w') as f:
        json.dump(json_data, f)
    print(f"已保存为 {args.output}")

if __name__ == '__main__':
    main() 