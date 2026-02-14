JP_MONTHS = {
    1: "睦月",
    2: "如月",
    3: "弥生",
    4: "卯月",
    5: "皐月",
    6: "水無月",
    7: "文月",
    8: "葉月",
    9: "長月",
    10: "神無月",
    11: "霜月",
    12: "師走",
}


def print_jp_month(month):
    print(f"{month}月は和風月名で{JP_MONTHS[month]}です")


print_jp_month(3)
print_jp_month(12)
