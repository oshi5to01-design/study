addresses = {
    "鈴木": "suzuki@example.com",
    "田中": "tanaka@example.com",
    "山田": "yamada@example.com",
    "佐藤": "sato@gmail.com",
}

gmail_addresses = {}
for name, address in addresses.items():
    if address.endswith("@gmail.com"):
        gmail_addresses[name] = address

print(gmail_addresses)
