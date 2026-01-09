import random


def play_game():
    select_number = random.randint(1, 100)
    print("start")
    attempts = 0
    while True:
        user_input = input("入力してください")
        guess = int(user_input)
        attempts = attempts + 1
        if guess == select_number:
            print(f"正解！{attempts}回目で成功！")
            break
        elif guess > select_number:
            print("もっとちいさいよ")
        else:
            print("もっとおおきいよ")


if __name__ == "__main__":
    play_game()
