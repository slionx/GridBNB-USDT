# BNB/USDT 自动化网格交易机器人

这是一个基于 Python 的自动化交易程序，专为币安 (Binance) 交易所的 BNB/USDT 交易对设计。该程序采用网格交易策略，旨在通过动态调整网格和仓位来捕捉市场波动，并内置风险管理机制。

## 核心功能

*   **自动化网格交易**: 针对 BNB/USDT 交易对执行网格买卖策略。
*   **动态网格调整**: 根据市场波动率自动调整网格大小 (`config.py` 中的 `GRID_PARAMS`)。
*   **风险管理**:
    *   最大回撤限制 (`MAX_DRAWDOWN`)
    *   每日亏损限制 (`DAILY_LOSS_LIMIT`)
    *   最大仓位比例限制 (`MAX_POSITION_RATIO`)
*   **Web 用户界面**: 提供一个简单的 Web 界面 (通过 `web_server.py`)，用于实时监控交易状态、账户信息、订单和调整配置。
*   **状态持久化**: 将交易状态保存到 `data/` 目录下的 JSON 文件中，以便重启后恢复。
*   **通知推送**: 可通过 PushPlus 发送重要事件和错误通知 (`PUSHPLUS_TOKEN`)。
*   **日志记录**: 详细的运行日志记录在 `trading_system.log` 文件中。

## 环境要求

*   Python 3.8+
*   依赖库见 `requirements.txt` 文件。

## 安装步骤

1.  **克隆仓库**:
    ```bash
    git clone <你的仓库HTTPS或SSH地址>
    cd GridBNB-USDT
    ```

2.  **创建并激活虚拟环境**:
    *   **Windows**:
        ```bash
        python -m venv .venv
        .\.venv\Scripts\activate
        ```
    *   **Linux / macOS**:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

## 配置

1.  **创建 `.env` 文件**:
    在项目根目录下创建一个名为 `.env` 的文件。

2.  **配置环境变量**:
    在 `.env` 文件中添加以下必要的环境变量，并填入你的信息：
    ```dotenv
    # 币安 API (必须)
    BINANCE_API_KEY=YOUR_BINANCE_API_KEY
    BINANCE_API_SECRET=YOUR_BINANCE_API_SECRET

    # PushPlus Token (可选, 用于消息推送)
    PUSHPLUS_TOKEN=YOUR_PUSHPLUS_TOKEN

    # 初始设置 (可选, 影响首次运行和统计)
    INITIAL_PRINCIPAL=1000.0  # 你的初始总资产 (USDT)
    INITIAL_BASE_PRICE=600.0   # 你认为合适的初始基准价格 (用于首次启动确定方向)
    ```
    *   **重要**: 确保你的币安 API Key 具有现货交易权限，但**不要**开启提现权限。

3.  **调整交易参数 (可选)**:
    你可以根据自己的策略需求修改 `config.py` 文件中的参数，例如：
    *   `SYMBOL`: 交易对 (默认为 'BNB/USDT')
    *   `INITIAL_GRID`: 初始网格大小 (%)
    *   `MIN_TRADE_AMOUNT`: 最小交易金额 (USDT)
    *   `MAX_POSITION_RATIO`, `MIN_POSITION_RATIO`: 最大/最小仓位比例
    *   风险参数 (`MAX_DRAWDOWN`, `DAILY_LOSS_LIMIT`)
    *   波动率与网格对应关系 (`GRID_PARAMS['volatility_threshold']`)

## 运行模式说明

本项目支持三种运行模式，便于实盘、模拟盘和历史回测灵活切换：

- **live（实盘）**：默认模式，直接连接币安API，真实下单。
- **simulate（模拟盘）**：以实时行情为基础，所有下单、成交、账户变动均在本地虚拟账户中模拟，不与真实交易所交互，适合策略仿真和风控测试。
- **backtest（回测）**：以本地历史K线/成交数据为行情源，完全离线模拟账户、撮合、风控等，适合策略历史复盘和参数优化。

### 启动参数与环境变量

可通过命令行参数或环境变量灵活切换模式和配置：

- `--mode` 或 `TRADING_MODE`：选择运行模式（live/simulate/backtest）
- `--kline` 或 `BACKTEST_KLINE_PATH`：回测模式下指定历史K线数据文件（JSON格式）
- `--init-usdt`、`--init-bnb`：指定初始资金

**示例：**

```bash
# 实盘模式（默认）
python main.py

# 模拟盘模式，初始资金10000 USDT
python main.py --mode simulate --init-usdt 10000

# 回测模式，指定K线文件和初始资金
python3 main.py --mode backtest --kline bnbusdt_1h.json --init-usdt 5000 --init-bnb 5
```

## 回测数据准备与结果导出

- 回测K线文件需为JSON数组格式，每行为 `[timestamp, open, high, low, close]`。
- 回测结束后，可通过MockExchangeClient的 `export_trades_to_csv`、`export_trades_to_json`、`export_equity_curve_to_csv` 方法导出成交记录和资金曲线。
- 默认导出文件为 `backtest_trades.csv`、`backtest_equity_curve.csv`，可在Web端"回测结果"卡片中可视化查看。

## Web端回测结果可视化

- 启动Web服务后，访问 `http://localhost:58181`，可在"回测结果"卡片中查看最近成交、资金曲线和简要统计。
- 支持与实盘/模拟盘参数对比，便于策略调优。

## 插件式回测架构说明

- 所有交易所交互均通过 `IExchangeClient` 接口协议，主流程可无缝切换实盘、模拟盘、回测等多种实现。
- MockExchangeClient、SimulateExchangeClient分别支持历史回测和实时模拟盘，便于策略开发、测试和复盘。
- 未来可扩展多币种、多策略、多账户等高级功能。

## 单元测试

- 推荐使用pytest运行单元测试，覆盖MockExchangeClient、SimulateExchangeClient等关键模块：

```bash
pytest tests/test_exchange_clients.py
```

## 运行

在激活虚拟环境的项目根目录下运行主程序：

```bash
python main.py
```

程序启动后将开始连接交易所、初始化状态并执行交易逻辑。

## Web 界面

程序启动后，会自动运行一个 Web 服务器。你可以通过浏览器访问以下地址来监控和管理交易机器人：

`http://127.0.0.1:8080`

*注意: 端口号 (8080) 可能在 `web_server.py` 中定义，如果无法访问请检查该文件。*

Web 界面可以让你查看当前状态、账户余额、持仓、挂单、历史记录，并可能提供一些手动操作或配置调整的功能。

## 日志

程序的运行日志会输出到控制台，并同时记录在项目根目录下的 `trading_system.log` 文件中。

## 注意事项

*   **交易风险**: 所有交易决策均由程序自动执行，但市场存在固有风险。请务必了解策略原理和潜在风险，并自行承担交易结果。不建议在未充分理解和测试的情况下投入大量资金。
*   **API Key 安全**: 妥善保管你的 API Key 和 Secret，不要泄露给他人。
*   **配置合理性**: 确保 `config.py` 和 `.env` 中的配置符合你的预期和风险承受能力。

## 贡献

欢迎提交 Pull Requests 或 Issues 来改进项目。

## 历史K线数据拉取

项目已集成自动化K线数据拉取脚本，便于回测数据准备：

- 脚本位置：`scripts/fetch_kline.py`
- 功能：自动拉取币安任意币对、任意K线周期的历史数据，输出为MockExchangeClient兼容的JSON格式。

### 使用方法

```bash
# 拉取BNB/USDT 1小时K线，2021年全年，保存为bnbusdt_1h.json
python scripts/fetch_kline.py --symbol BNB/USDT --timeframe 1h --since 2021-01-01T00:00:00Z --end 2022-01-01T00:00:00Z --output bnbusdt_1h.json

# 拉取BTC/USDT 4小时K线，近半年
python scripts/fetch_kline.py --symbol BTC/USDT --timeframe 4h --since 2023-01-01T00:00:00Z --output btcusdt_4h.json
```

- 参数说明：
  - `--symbol` 币对（如BNB/USDT、BTC/USDT）
  - `--timeframe` K线周期（如1h、4h、1d）
  - `--since` 起始时间（UTC，格式如2021-01-01T00:00:00Z）
  - `--end` 结束时间（UTC，格式如2022-01-01T00:00:00Z）
  - `--output` 输出文件名（如bnbusdt_1h.json）

- 输出格式：JSON数组，每行为 `[timestamp, open, high, low, close]`，可直接用于MockExchangeClient回测。

- 支持自动分页拉取，进度实时显示，异常自动重试。
