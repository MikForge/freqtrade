#!/usr/bin/env python3
"""
简化的训练和回测自动化脚本
执行回测后直接读取最新的回测结果JSON文件
"""
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加当前目录到 Python 路径以支持模块导入
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
# 配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def get_venv_python():
    """获取虚拟环境中的Python路径"""
    venv_python = Path(__file__).parent / ".venv" / "bin" / "python"
    return str(venv_python) if venv_python.exists() else sys.executable


def validate_environment():
    """验证运行环境"""
    issues = []

    # 检查Python环境
    python_path = get_venv_python()
    if not Path(python_path).exists():
        issues.append(f"Python路径不存在: {python_path}")

    # 检查配置文件
    config_file = Path(__file__).parent / "user_data" / "config_dev.json"
    if not config_file.exists():
        issues.append(f"配置文件不存在: {config_file}")

    # 检查必要目录
    user_data_dir = Path(__file__).parent / "user_data"
    if not user_data_dir.exists():
        issues.append(f"user_data目录不存在: {user_data_dir}")

    if issues:
        logger.error("❌ 环境验证失败:")
        for issue in issues:
            logger.error(f"   - {issue}")
        return False
    else:
        logger.info("✅ 环境验证通过")
        return True


def run_backtest(python_path):
    """执行回测"""
    logger.info("🔄 开始回测...")

    # 检查配置文件是否存在
    config_file = Path("user_data") / "config_dev.json"
    if not config_file.exists():
        logger.error(f"❌ 配置文件不存在: {config_file}")
        return False, f"配置文件不存在: {config_file}"

    max_retries = 3
    for attempt in range(max_retries):
        if attempt > 0:
            wait_time = 10 * attempt
            logger.info(f"第{attempt + 1}次重试，等待{wait_time}秒...")
            time.sleep(wait_time)

        try:
            # 执行回测
            result = subprocess.run([
                python_path, "-m", "freqtrade.main",
                "backtesting",
                "--config", str(config_file),
                "--userdir", "user_data",
                "--timerange", "20240601-20240701",
                "--cache", "none",
                "--export", "trades",
                "--eps"  # 启用边缘仓位调整
            ], cwd=Path(__file__).parent, check=True, capture_output=True, text=True)

            logger.info("✅ 回测完成")
            return True, result.stdout.strip()

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 回测失败 (尝试 {attempt + 1}/{max_retries})")
            logger.error(
                f"   错误信息: {e.stderr.strip() if e.stderr else str(e)}")
            if attempt == max_retries - 1:
                logger.error("回测失败，已尝试所有重试次数")
                return False, e.stderr.strip() if e.stderr else str(e)

    return False, "回测失败"


def _get_latest_backtest_file():
    """获取最新的回测结果文件路径"""
    backtest_dir = Path(__file__).parent / "user_data" / "backtest_results"
    last_result_file = backtest_dir / ".last_result.json"

    with last_result_file.open('r', encoding='utf-8') as f:
        last_result = json.load(f)

    latest_filename = last_result["latest_backtest"]
    return backtest_dir / latest_filename


def _extract_trade_metrics(trades):
    """从交易数据中提取最佳/最差交易指标"""
    if not trades:
        return {"best_trade_pct": 0, "worst_trade_pct": 0}

    profit_ratios = [trade.get('profit_ratio', 0) for trade in trades]
    return {
        "best_trade_pct": max(profit_ratios) * 100,
        "worst_trade_pct": min(profit_ratios) * 100
    }


def _build_summary_metrics(strategy_data):
    """构建完整的SUMMARY METRICS数据结构"""
    trade_metrics = _extract_trade_metrics(strategy_data.get('trades', []))

    return {
        # 回测时间范围
        "backtesting_from": strategy_data.get('backtest_start', ''),
        "backtesting_to": strategy_data.get('backtest_end', ''),
        "max_open_trades": strategy_data.get('max_open_trades_setting', 0),

        # 交易统计
        "total_trades": strategy_data.get('total_trades', 0),
        "daily_avg_trades": strategy_data.get('trades_per_day', 0),
        "starting_balance": strategy_data.get('starting_balance', 0),
        "final_balance": strategy_data.get('final_balance', 0),
        "absolute_profit": strategy_data.get('profit_total_abs', 0),
        "total_profit_pct": strategy_data.get('profit_total', 0),
        "cagr_pct": strategy_data.get('cagr', 0),

        # 风险指标
        "sortino": strategy_data.get('sortino', 0),
        "sharpe": strategy_data.get('sharpe', 0),
        "calmar": strategy_data.get('calmar', 0),
        "profit_factor": strategy_data.get('profit_factor', 0),
        "expectancy": strategy_data.get('expectancy', 0),
        "expectancy_ratio": strategy_data.get('expectancy_ratio', 0),

        # 平均数据
        "avg_daily_profit_pct": (
            strategy_data.get('profit_total', 0) /
            strategy_data.get('backtest_days', 1)
            if strategy_data.get('backtest_days', 0) > 0 else 0
        ),
        "avg_stake_amount": strategy_data.get('avg_stake_amount', 0),
        "total_trade_volume": strategy_data.get('total_volume', 0),

        # 最佳/最差数据
        "best_pair": strategy_data.get('best_pair', ''),
        "worst_pair": strategy_data.get('worst_pair', ''),
        "best_trade_pct": trade_metrics["best_trade_pct"],
        "worst_trade_pct": trade_metrics["worst_trade_pct"],
        "best_day": strategy_data.get('backtest_best_day_abs', 0),
        "worst_day": strategy_data.get('backtest_worst_day_abs', 0),

        # 胜负统计
        "winning_days": strategy_data.get('winning_days', 0),
        "draw_days": strategy_data.get('draw_days', 0),
        "losing_days": strategy_data.get('losing_days', 0),
        "wins": strategy_data.get('wins', 0),
        "losses": strategy_data.get('losses', 0),
        "winrate": strategy_data.get('winrate', 0),

        # 持仓时间
        "avg_duration_winners": strategy_data.get('winner_holding_avg', ''),
        "avg_duration_losers": strategy_data.get('loser_holding_avg', ''),
        "max_consecutive_wins": strategy_data.get('max_consecutive_wins', 0),
        "max_consecutive_losses": strategy_data.get('max_consecutive_losses', 0),

        # 订单统计
        "rejected_entry_signals": strategy_data.get('rejected_signals', 0),
        "entry_timeouts": strategy_data.get('timedout_entry_orders', 0),
        "exit_timeouts": strategy_data.get('timedout_exit_orders', 0),

        # 回撤数据
        "min_balance": strategy_data.get('csum_min', 0),
        "max_balance": strategy_data.get('csum_max', 0),
        "max_drawdown_account_pct": strategy_data.get('max_drawdown_account', 0),
        "absolute_drawdown_abs": strategy_data.get('max_drawdown_abs', 0),
        "drawdown_high": strategy_data.get('max_drawdown_high', 0),
        "drawdown_low": strategy_data.get('max_drawdown_low', 0),
        "drawdown_start": strategy_data.get('drawdown_start', ''),
        "drawdown_end": strategy_data.get('drawdown_end', ''),
        "market_change": strategy_data.get('market_change', 0)
    }


def _save_analysis_data(summary_metrics, strategy_name, source_file, output_dir):
    """保存分析数据到JSON文件"""
    analysis_dir = Path(output_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    output_file = analysis_dir / "latest_backtest_data.json"

    with output_file.open('w', encoding='utf-8') as f:
        json.dump({
            "strategy_name": strategy_name,
            "summary_metrics": summary_metrics,
            "extracted_at": datetime.now().isoformat(),
            "source_file": source_file
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 数据已保存到: {output_file}")
    return output_file


def _log_summary_metrics(summary_metrics):
    """显示关键指标日志"""
    logger.info("📈 SUMMARY METRICS:")
    logger.info(f"   回测时间: {summary_metrics['backtesting_from']} 到 "
                f"{summary_metrics['backtesting_to']}")
    logger.info(f"   总交易数/日均: {summary_metrics['total_trades']} / "
                f"{summary_metrics['daily_avg_trades']:.2f}")
    logger.info(f"   起始余额: {summary_metrics['starting_balance']:.2f} USDT")
    logger.info(f"   最终余额: {summary_metrics['final_balance']:.2f} USDT")
    logger.info(f"   绝对收益: {summary_metrics['absolute_profit']:.3f} USDT")
    logger.info(f"   总收益率: {summary_metrics['total_profit_pct']:.2%}")
    logger.info(f"   年化收益率(CAGR): {summary_metrics['cagr_pct']:.2%}")
    logger.info(f"   夏普比率: {summary_metrics['sharpe']:.3f}")
    logger.info(f"   索提诺比率: {summary_metrics['sortino']:.3f}")
    logger.info(f"   卡玛比率: {summary_metrics['calmar']:.3f}")
    logger.info(f"   胜率: {summary_metrics['winrate']:.2%}")
    logger.info(f"   最大回撤: {summary_metrics['max_drawdown_account_pct']:.2%}")
    logger.info(f"   市场变化: {summary_metrics['market_change']:.2%}")


def get_latest_backtest_data(output_dir=None):
    """
    从最新的回测结果中提取关键指标
    数据源：freqtrade backtest命令生成的JSON文件，
    位于 data["strategy"]["LiveDivSignalStrategy"] 节点

    Args:
        output_dir: 分析数据保存目录，如果为None则使用默认目录
    """
    logger.info("📊 读取最新回测结果...")

    # 如果没有指定输出目录，使用默认目录
    if output_dir is None:
        output_dir = Path(__file__).parent / "user_data" / "backtest_analysis"

    try:
        # 1. 获取最新回测文件
        latest_file = _get_latest_backtest_file()
        logger.info(f"📁 读取文件: {latest_file.name}")

        # 2. 读取回测数据
        with latest_file.open('r', encoding='utf-8') as f:
            data = json.load(f)

        strategy_name = list(data['strategy'].keys())[0]
        strategy_data = data['strategy'][strategy_name]

        # 3. 构建指标数据
        summary_metrics = _build_summary_metrics(strategy_data)

        # 4. 保存分析数据
        _save_analysis_data(summary_metrics, strategy_name,
                            latest_file.name, output_dir)

        # 5. 显示关键指标
        _log_summary_metrics(summary_metrics)

        return summary_metrics

    except Exception as e:
        logger.error(f"❌ 读取回测数据失败: {e}")
        return None


def main():
    """
    主函数

    Args:
        output_dir: 分析数据保存目录，如果为None则使用默认目录
    """
    logger.info("🚀 开始自动化训练和回测")

    # 验证运行环境
    if not validate_environment():
        logger.error("环境验证失败，终止执行")
        sys.exit(1)

    python_path = get_venv_python()
    logger.info(f"使用Python: {python_path}")

    try:
        # 步骤1: XGBoost训练
        logger.info("📊 步骤1: 开始XGBoost训练...")
        try:
            logger.info("🔧 执行: XGBoost训练")

            # 直接导入并调用模块
            from user_data.strategies.xgbhelp.main import main as xgb_main
            # 可以传递参数，例如: xgb_main(config_path, data_path)
            xgb_main()  # 直接调用训练函数

            logger.info("✅ XGBoost训练 成功")

        except Exception as e:
            logger.error(f"❌ XGBoost训练 失败: {e}")
            logger.error("XGBoost训练失败，终止流程")
            sys.exit(1)

        # 步骤2: 执行回测，传递训练结果
        success, backtest_output = run_backtest(python_path)
        if not success:
            logger.error("回测失败，尝试读取已有结果...")

        # 动态导入所需模块
        try:
            from user_data.strategies.common_utils.version import get_latest_version_folder
            from user_data.strategies.common_utils.struct import StructureSubtype
        except ImportError as e:
            logger.error(f"导入模块失败: {e}")
            logger.error("将使用默认路径...")
            backtest_data_dir = "user_data/strategies/xgbhelp/files/modelanalyze/is_rp/"
            backtest_data = get_latest_backtest_data(backtest_data_dir)
        else:
            # 步骤3: 读取最新回测数据
            backtest_data_dir = get_latest_version_folder(
                base_path=f"user_data/strategies/xgbhelp/files/modelanalyze/{StructureSubtype.IS_RP.value}/"
            )
            backtest_data = get_latest_backtest_data(backtest_data_dir)

        if backtest_data:
            logger.info("✅ 流程完成!")
            logger.info("📁 查看结果:")
            # 显示实际的保存路径
            logger.info(
                f"   - 回测数据: {backtest_data_dir}/latest_backtest_data.json")
        else:
            logger.error("❌ 无法获取回测数据")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断")
        sys.exit(1)


if __name__ == "__main__":

    main()
