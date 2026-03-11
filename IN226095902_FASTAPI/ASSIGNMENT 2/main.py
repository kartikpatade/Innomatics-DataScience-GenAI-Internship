from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI()

# ── Data ──────────────────────────────────────────────────────
store_items = [
    {"id": 1, "name": "Wireless Mouse",      "price": 799,  "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook",            "price": 149,  "category": "Stationery",  "in_stock": True},
    {"id": 3, "name": "USB Hub",             "price": 999,  "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set",             "price": 49,   "category": "Stationery",  "in_stock": True},
    {"id": 5, "name": "Laptop Stand",        "price": 1299, "category": "Electronics", "in_stock": True},
    {"id": 6, "name": "Mechanical Keyboard", "price": 2499, "category": "Electronics", "in_stock": True},
    {"id": 7, "name": "Webcam",              "price": 1899, "category": "Electronics", "in_stock": False},
]

feedback_list = []
order_list    = []
order_counter = 1


# ── Pydantic Models ───────────────────────────────────────────
class CustomerFeedback(BaseModel):
    customer_name: str           = Field(..., min_length=2, max_length=100)
    product_id:    int           = Field(..., gt=0)
    rating:        int           = Field(..., ge=1, le=5)
    comment:       Optional[str] = Field(None, max_length=300)


class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=50)


class BulkOrder(BaseModel):
    company_name:  str            = Field(..., min_length=2)
    contact_email: str            = Field(..., min_length=5)
    items:         List[OrderItem] = Field(..., min_length=1)


class SingleOrder(BaseModel):
    customer_name: str = Field(..., min_length=2)
    product_id:    int = Field(..., gt=0)
    quantity:      int = Field(..., gt=0, le=50)


# ── Day 1 Endpoints (kept as-is) ─────────────────────────────
@app.get("/products")
def all_products():
    return {"products": store_items, "total": len(store_items)}


@app.get("/products/category/{category_name}")
def filter_by_category(category_name: str):
    filtered = [item for item in store_items if item["category"] == category_name]
    if not filtered:
        return {"error": "No products found in this category"}
    return {"category": category_name, "products": filtered, "total": len(filtered)}


@app.get("/products/instock")
def available_products():
    available = [item for item in store_items if item["in_stock"]]
    return {"in_stock_products": available, "count": len(available)}


@app.get("/products/deals")
def best_and_premium():
    return {
        "best_deal":    min(store_items, key=lambda x: x["price"]),
        "premium_pick": max(store_items, key=lambda x: x["price"]),
    }


# ── Q1 — Filter with min_price (+ existing filters) ──────────
@app.get("/products/filter")
def filter_products(
    category:  str = Query(None, description="Filter by category"),
    max_price: int = Query(None, description="Maximum price"),
    min_price: int = Query(None, description="Minimum price"),
):
    result = store_items[:]
    if category:
        result = [p for p in result if p["category"] == category]
    if max_price:
        result = [p for p in result if p["price"] <= max_price]
    if min_price:
        result = [p for p in result if p["price"] >= min_price]
    return {"products": result, "total": len(result)}


# ── Q2 — Get only price of a product ─────────────────────────
@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    for item in store_items:
        if item["id"] == product_id:
            return {"name": item["name"], "price": item["price"]}
    return {"error": "Product not found"}


# ── Q3 — Accept customer feedback ────────────────────────────
@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback_list.append(data.dict())
    return {
        "message":        "Feedback submitted successfully",
        "feedback":       data.dict(),
        "total_feedback": len(feedback_list),
    }


# ── Q4 — Product summary dashboard ───────────────────────────
@app.get("/products/summary")
def product_summary():
    in_stock  = [p for p in store_items if p["in_stock"]]
    out_stock = [p for p in store_items if not p["in_stock"]]
    priciest  = max(store_items, key=lambda p: p["price"])
    cheapest  = min(store_items, key=lambda p: p["price"])
    cats      = list(set(p["category"] for p in store_items))
    return {
        "total_products":     len(store_items),
        "in_stock_count":     len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive":     {"name": priciest["name"], "price": priciest["price"]},
        "cheapest":           {"name": cheapest["name"],  "price": cheapest["price"]},
        "categories":         cats,
    }


# ── Q5 — Bulk order ───────────────────────────────────────────
@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
    confirmed, failed, grand_total = [], [], 0
    for entry in order.items:
        product = next((p for p in store_items if p["id"] == entry.product_id), None)
        if not product:
            failed.append({"product_id": entry.product_id, "reason": "Product not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": entry.product_id, "reason": f"{product['name']} is out of stock"})
        else:
            subtotal = product["price"] * entry.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": entry.quantity, "subtotal": subtotal})
    return {
        "company":     order.company_name,
        "confirmed":   confirmed,
        "failed":      failed,
        "grand_total": grand_total,
    }


# ── BONUS — Single order with pending/confirmed status ────────
@app.post("/orders")
def place_order(order: SingleOrder):
    global order_counter
    product = next((p for p in store_items if p["id"] == order.product_id), None)
    if not product:
        return {"error": "Product not found"}
    if not product["in_stock"]:
        return {"error": f"{product['name']} is out of stock"}
    new_order = {
        "order_id":      order_counter,
        "customer_name": order.customer_name,
        "product":       product["name"],
        "quantity":      order.quantity,
        "total":         product["price"] * order.quantity,
        "status":        "pending",
    }
    order_list.append(new_order)
    order_counter += 1
    return {"message": "Order placed", "order": new_order}


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for order in order_list:
        if order["order_id"] == order_id:
            return {"order": order}
    return {"error": "Order not found"}


@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    for order in order_list:
        if order["order_id"] == order_id:
            order["status"] = "confirmed"
            return {"message": "Order confirmed", "order": order}
    return {"error": "Order not found"}


# ── Day 1 search (kept) ───────────────────────────────────────
@app.get("/store/summary")
def store_summary():
    in_stock = [item for item in store_items if item["in_stock"]]
    cats     = list(set(item["category"] for item in store_items))
    return {
        "store_name":     "My E-commerce Store",
        "total_products": len(store_items),
        "in_stock":       len(in_stock),
        "out_of_stock":   len(store_items) - len(in_stock),
        "categories":     cats,
    }


@app.get("/products/search/{keyword}")
def search_by_name(keyword: str):
    matches = [item for item in store_items if keyword.lower() in item["name"].lower()]
    if not matches:
        return {"message": "No products matched your search"}
    return {"keyword": keyword, "results": matches, "total_matches": len(matches)}
