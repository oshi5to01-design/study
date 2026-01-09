import random


def play_game():
    secret_number = random.randint(1, 100)
    attempts = 0
    print("1~100の数字を当ててね")
    while True:
        user_input = input("数字を入力してください")
        guess = int(user_input)
        attempts = attempts + 1
        if guess == secret_number:
            print(f"正解！{attempts}回目で当たりました！")
            break
        elif guess > secret_number:
            print("もっと小さいよ")
        else:
            print("もっと大きいよ")


if __name__ == "__main__":
    play_game()
