results = []
for i in range(1, 101):
    if i % 15 == 0:
        val = "FizzBuzz"
    elif i % 3 == 0:
        val = "Fizz"
    elif i % 5 == 0:
        val = "Buzz"
    else:
        val = str(i)
    results.append(val)
print("\n".join(results))
