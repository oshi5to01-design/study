import time

seconds = 5

print("カウントダウン開始")

while seconds > 0:
    print(seconds)

    time.sleep(1)

    seconds = seconds - 1

print("発射！")
