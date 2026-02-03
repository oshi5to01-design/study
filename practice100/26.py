odd_numbers = [1, 3, 5, 7]
even_numbers = [2, 4, 6, 8]
odd_numbers.append(9)
target = 8
if target in even_numbers:
    even_numbers.remove(target)
else:
    print(f"{target}は見つかりませんでした。")

print(odd_numbers)
print(even_numbers)
