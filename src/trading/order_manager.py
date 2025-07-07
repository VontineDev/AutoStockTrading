#!/usr/bin/env python3
"""
주문 관리 모듈
- 매수/매도 주문 처리
- 주문 상태 관리
- 주문 이력 추적
- 슬리피지 및 수수료 적용
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

class OrderType(Enum):
    """주문 유형"""
    MARKET = "MARKET"  # 시장가
    LIMIT = "LIMIT"    # 지정가

class OrderSide(Enum):
    """매매 구분"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "PENDING"      # 대기
    FILLED = "FILLED"        # 체결
    CANCELLED = "CANCELLED"  # 취소
    REJECTED = "REJECTED"    # 거부

@dataclass
class Order:
    """주문 정보"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None  # 지정가 주문시만 사용
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    commission: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.order_id is None:
            self.order_id = f"{self.symbol}_{self.side.value}_{self.created_at.strftime('%Y%m%d_%H%M%S')}"

class OrderManager:
    """주문 관리 클래스"""
    
    def __init__(self, commission_rate: float = 0.00015, slippage_rate: float = 0.001):
        """
        주문 관리자 초기화
        
        Args:
            commission_rate: 수수료율 (기본: 0.015%)
            slippage_rate: 슬리피지율 (기본: 0.1%)
        """
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        # 주문 관리
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        
        # 로깅
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_market_order(self, symbol: str, side: OrderSide, quantity: int) -> Order:
        """시장가 주문 생성"""
        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity
        )
        
        self.orders[order.order_id] = order
        self.logger.info(f"시장가 주문 생성: {order.order_id} - {symbol} {side.value} {quantity}주")
        return order
    
    def create_limit_order(self, symbol: str, side: OrderSide, quantity: int, price: float) -> Order:
        """지정가 주문 생성"""
        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price
        )
        
        self.orders[order.order_id] = order
        self.logger.info(f"지정가 주문 생성: {order.order_id} - {symbol} {side.value} {quantity}주 @ {price:,.0f}원")
        return order
    
    def execute_order(self, order_id: str, market_price: float, available_quantity: int = None) -> bool:
        """주문 체결 처리"""
        if order_id not in self.orders:
            self.logger.error(f"주문 ID를 찾을 수 없음: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        if order.status != OrderStatus.PENDING:
            self.logger.warning(f"이미 처리된 주문: {order_id} (상태: {order.status.value})")
            return False
        
        # 체결 가능 여부 확인
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and market_price > order.price:
                self.logger.info(f"지정가 매수 주문 미체결: 시장가 {market_price:,.0f} > 주문가 {order.price:,.0f}")
                return False
            elif order.side == OrderSide.SELL and market_price < order.price:
                self.logger.info(f"지정가 매도 주문 미체결: 시장가 {market_price:,.0f} < 주문가 {order.price:,.0f}")
                return False
        
        # 체결 가격 계산 (슬리피지 적용)
        if order.side == OrderSide.BUY:
            filled_price = market_price * (1 + self.slippage_rate)  # 매수시 불리하게
        else:
            filled_price = market_price * (1 - self.slippage_rate)  # 매도시 불리하게
        
        # 지정가 주문의 경우 지정가보다 유리하게 체결되지 않음
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                filled_price = min(filled_price, order.price)
            else:
                filled_price = max(filled_price, order.price)
        
        # 체결 수량 결정
        filled_quantity = order.quantity
        if available_quantity is not None and available_quantity < order.quantity:
            filled_quantity = available_quantity
        
        if filled_quantity <= 0:
            order.status = OrderStatus.REJECTED
            self.logger.warning(f"주문 거부: {order_id} - 체결 가능 수량 부족")
            return False
        
        # 수수료 계산
        gross_amount = filled_quantity * filled_price
        commission = gross_amount * self.commission_rate
        
        # 주문 상태 업데이트
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.filled_price = filled_price
        order.filled_quantity = filled_quantity
        order.commission = commission
        
        # 이력에 추가
        self.order_history.append(order)
        
        self.logger.info(f"주문 체결: {order_id} - {filled_quantity}주 @ {filled_price:,.0f}원 (수수료: {commission:,.0f}원)")
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if order_id not in self.orders:
            self.logger.error(f"주문 ID를 찾을 수 없음: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        if order.status != OrderStatus.PENDING:
            self.logger.warning(f"취소할 수 없는 주문: {order_id} (상태: {order.status.value})")
            return False
        
        order.status = OrderStatus.CANCELLED
        self.order_history.append(order)
        
        self.logger.info(f"주문 취소: {order_id}")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """주문 정보 조회"""
        return self.orders.get(order_id)
    
    def get_pending_orders(self, symbol: str = None) -> List[Order]:
        """대기 중인 주문 목록"""
        pending_orders = [
            order for order in self.orders.values() 
            if order.status == OrderStatus.PENDING
        ]
        
        if symbol:
            pending_orders = [order for order in pending_orders if order.symbol == symbol]
        
        return pending_orders
    
    def get_filled_orders(self, symbol: str = None) -> List[Order]:
        """체결된 주문 목록"""
        filled_orders = [
            order for order in self.order_history 
            if order.status == OrderStatus.FILLED
        ]
        
        if symbol:
            filled_orders = [order for order in filled_orders if order.symbol == symbol]
        
        return filled_orders
    
    def get_order_summary(self) -> Dict[str, int]:
        """주문 현황 요약"""
        summary = {
            'total': len(self.orders),
            'pending': len([o for o in self.orders.values() if o.status == OrderStatus.PENDING]),
            'filled': len([o for o in self.order_history if o.status == OrderStatus.FILLED]),
            'cancelled': len([o for o in self.order_history if o.status == OrderStatus.CANCELLED]),
            'rejected': len([o for o in self.order_history if o.status == OrderStatus.REJECTED])
        }
        return summary
    
    def clear_completed_orders(self):
        """완료된 주문들을 활성 주문 목록에서 제거"""
        completed_orders = [
            order_id for order_id, order in self.orders.items()
            if order.status != OrderStatus.PENDING
        ]
        
        for order_id in completed_orders:
            del self.orders[order_id]
        
        self.logger.info(f"완료된 주문 {len(completed_orders)}개 정리")
    
    def reset(self):
        """주문 관리자 초기화"""
        self.orders.clear()
        self.order_history.clear()
        self.logger.info("주문 관리자 초기화 완료") 