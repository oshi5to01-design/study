import random


def play_game():
    select_number = random.randint(1, 100)
    attempts = 0
    print("ゲームスタート")

    while True:
        user_input = input("入力してください")
        guess = int(user_input)
        attempts = attempts + 1
        if guess == select_number:
            print(f"正解！{attempts}回目で成功")
            break
        elif guess > select_number:
            print("もっと小さいよ")
        else:
            print("もっと大きいよ")


if __name__ == "__main__":
    play_game()
