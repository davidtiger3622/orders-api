from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.cache import acquire_lock, release_lock
from app.db import get_db
from app.models import Order, OrderItem

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItemIn(BaseModel):
    product_name: str
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    customer_email: str
    idempotency_key: str
    items: list[OrderItemIn]


@router.post("/checkout")
def checkout(payload: OrderCreate, db: Session = Depends(get_db)):
    existing = db.query(Order).filter(
        Order.idempotency_key == payload.idempotency_key
    ).first()
    if existing:
        return {"order_id": existing.id, "status": existing.status}

    lock_acquired = acquire_lock(payload.idempotency_key)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Checkout already in progress")

    try:
        total = sum(item.quantity * item.unit_price for item in payload.items)
        order = Order(
            customer_email=payload.customer_email,
            idempotency_key=payload.idempotency_key,
            total_amount=total,
            status="confirmed",
        )
        db.add(order)
        db.flush()

        for item in payload.items:
            db.add(OrderItem(
                order_id=order.id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            ))

        db.commit()
        db.refresh(order)
        return {"order_id": order.id, "status": order.status}
    finally:
        release_lock(payload.idempotency_key)


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order.id,
        "status": order.status,
        "total_amount": order.total_amount,
        "customer_email": order.customer_email,
    }
