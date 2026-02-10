items = [
    {"name": "りんご", "unit_price": 100, "quantity": 3},
    {"name": "みかん", "unit_price": 50, "quantity": 5},
    {"name": "バナナ", "unit_price": 80, "quantity": 2},
]

total_price = 0
for item in items:
    price = item["unit_price"] * item["quantity"]
    total_price += price
print(total_price)
