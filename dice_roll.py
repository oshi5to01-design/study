import random

print("サイコロゲーム")

dice_roll = random.randint(1, 6)
print(f"サイコロの目は{dice_roll}desu")

if dice_roll == 6:
    print("おめ")
