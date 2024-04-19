import json
import os

def convert_cookies_for_selenium(input_file_path):
    if not os.path.exists(input_file_path):
        print(f"Couldn't find file: {input_file_path}")
        return

    output_file_path = os.path.splitext(input_file_path)[0] + "_converted.json"

    with open(input_file_path, 'r') as file:
        cookies = json.load(file)

    formatted_cookies = []
    for cookie in cookies:
        formatted_cookie = {key: cookie[key] for key in cookie if key != 'expiry' and key in ['name', 'value', 'domain', 'path', 'secure']}
        formatted_cookies.append(formatted_cookie)

    with open(output_file_path, 'w') as file:
        json.dump(formatted_cookies, file)

    print(f"Cookies converted and saved to: {output_file_path}")

input_path = input("Enter path to cookies file: ").strip('"')

convert_cookies_for_selenium(input_path)
