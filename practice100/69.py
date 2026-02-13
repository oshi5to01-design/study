numbers = [14, 32, 80, 1, 9]


def is_even(num):
    if num % 2 == 0:
        return True


for number in numbers:
    if is_even(number):
        print(f"{number}は偶数")
    else:
        print(f"{number}は奇数")
