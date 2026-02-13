numbers = [14, 32, 80, 1, 9]


def sum_and_avg(list):

    sum_number = sum(list)
    avg_number = sum_number / len(list)
    return sum_number, avg_number


sum, avg = sum_and_avg(numbers)
print(sum, avg)
