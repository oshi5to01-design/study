words = ["Apple", "banana", "Cherry", "lemon"]


def modify_words(word):
    first_char = word[0]
    if first_char.isupper():
        return word.upper()
    else:
        return word


modified_words = []
for word in words:
    m_word = modify_words(word)
    modified_words.append(m_word)

print(modified_words)
