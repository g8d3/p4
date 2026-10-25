"""EchoLike Liquidity paper pilot: simple PMM + status.json exporter (paper_trade only)."""
import json
import os
import time
from decimal import Decimal
from typing import Dict, List

from pydantic import Field

from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.common import MarketDict, OrderType, PriceType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate
from hummingbot.core.event.events import OrderFilledEvent
from hummingbot.strategy.strategy_v2_base import StrategyV2Base, StrategyV2ConfigBase

STATUS_PATH = "/home/hummingbot/data/status.json"
EXPORT_EVERY = 120  # seconds


class EchoPMMConfig(StrategyV2ConfigBase):
    script_file_name: str = os.path.basename(__file__)
    controllers_config: List[str] = []
    exchange: str = Field("binance_paper_trade")
    trading_pair: str = Field("ETH-USDT")
    order_amount: Decimal = Field(Decimal("0.01"))
    bid_spread: Decimal = Field(Decimal("0.001"))
    ask_spread: Decimal = Field(Decimal("0.001"))
    order_refresh_time: int = Field(15)

    def update_markets(self, markets: MarketDict) -> MarketDict:
        markets[self.exchange] = markets.get(self.exchange, set()) | {self.trading_pair}
        return markets


class EchoPMM(StrategyV2Base):
    create_timestamp = 0

    def __init__(self, connectors: Dict[str, ConnectorBase], config: EchoPMMConfig):
        super().__init__(connectors, config)
        self.config = config
        self.started = time.time()
        self.orders_placed = 0
        self.fills = []
        self.start_bal = None
        self.last_export = 0

    def _conn(self):
        return self.connectors[self.config.exchange]

    def _bals(self):
        base, quote = self.config.trading_pair.split("-")
        c = self._conn()
        return Decimal(str(c.get_balance(base))), Decimal(str(c.get_balance(quote)))

    def on_tick(self):
        c = self._conn()
        mid = c.get_price_by_type(self.config.trading_pair, PriceType.MidPrice)
        if self.start_bal is None and mid and mid > 0:
            self.start_bal = self._bals()
        if self.create_timestamp <= self.current_timestamp:
            for o in self.get_active_orders(connector_name=self.config.exchange):
                self.cancel(self.config.exchange, o.trading_pair, o.client_order_id)
            props = [
                OrderCandidate(trading_pair=self.config.trading_pair, is_maker=True, order_type=OrderType.LIMIT,
                               order_side=TradeType.BUY, amount=self.config.order_amount,
                               price=mid * (Decimal(1) - self.config.bid_spread)),
                OrderCandidate(trading_pair=self.config.trading_pair, is_maker=True, order_type=OrderType.LIMIT,
                               order_side=TradeType.SELL, amount=self.config.order_amount,
                               price=mid * (Decimal(1) + self.config.ask_spread)),
            ]
            for o in c.budget_checker.adjust_candidates(props, all_or_none=True):
                fn = self.buy if o.order_side == TradeType.BUY else self.sell
                fn(connector_name=self.config.exchange, trading_pair=o.trading_pair, amount=o.amount,
                   order_type=o.order_type, price=o.price)
                self.orders_placed += 1
            self.create_timestamp = self.config.order_refresh_time + self.current_timestamp
        if time.time() - self.last_export >= EXPORT_EVERY:
            self.export(mid)

    def did_fill_order(self, event: OrderFilledEvent):
        self.fills.append({"t": int(time.time()), "side": event.trade_type.name,
                           "amount": float(event.amount), "price": float(event.price)})
        self.fills = self.fills[-50:]
        self.fills_total = getattr(self, "fills_total", 0) + 1

    def export(self, mid):
        self.last_export = time.time()
        b, q = self._bals()
        pnl = None
        if self.start_bal and mid:
            pnl = float((b - self.start_bal[0]) * mid + (q - self.start_bal[1]))
        active = [{"side": "BUY" if o.is_buy else "SELL", "price": float(o.price), "amount": float(o.quantity)}
                  for o in self.get_active_orders(connector_name=self.config.exchange)]
        data = {
            "mode": "paper_trade",
            "strategy": "pure market making (simple PMM, V2 script)",
            "exchange": self.config.exchange,
            "pair": self.config.trading_pair,
            "spread_bps": [float(self.config.bid_spread * 10000), float(self.config.ask_spread * 10000)],
            "order_amount": float(self.config.order_amount),
            "refresh_s": self.config.order_refresh_time,
            "mid_price": float(mid) if mid else None,
            "started_at": int(self.started),
            "uptime_s": int(time.time() - self.started),
            "orders_placed": self.orders_placed,
            "fills_total": getattr(self, "fills_total", 0),
            "recent_fills": self.fills[-10:],
            "active_orders": active,
            "balances": {"base": float(b), "quote": float(q)},
            "paper_pnl_quote": round(pnl, 4) if pnl is not None else None,
            "updated_at": int(time.time()),
        }
        tmp = STATUS_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, STATUS_PATH)
