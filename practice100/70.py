def drink_price(drink_size, has_whip=False):
    price = 0
    if drink_size == "s":
        price += 100
    elif drink_size == "m":
        price += 200
    elif drink_size == "l":
        price += 300
    if has_whip:
        price += 100

    return price


price1 = drink_price("m", True)
price2 = drink_price("l")

print(price1)
print(price2)
