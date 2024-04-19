import requests
import json
from colorama import Fore, Style
import re
import datetime
import random
import time
import argparse
import os
import logging



# Function to create lock file
def create_lock_file(account_name):
    lock_file = f"{account_name}.lock"
    if os.path.exists(lock_file):
        print(f"Account {account_name} is already running. You can't run the same account twice.")
        exit()
    else:
        open(lock_file, 'w').close()
    return lock_file


# Function to check if chat has already been responded
def has_responded(account_name, chat_id):
    directory = 'responded'
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = os.path.join(directory, f'{account_name}_responded_chats.txt')
    if not os.path.exists(filename):
        open(filename, 'w').close()
    with open(filename, 'r') as file:
        responded_chats = file.read().splitlines()
    return chat_id in responded_chats


#Function to mark chat as responded
def mark_as_responded(account_name, chat_id):
    directory = 'responded'
    filename = os.path.join(directory, f'{account_name}_responded_chats.txt')
    with open(filename, 'a') as file:
        file.write(chat_id + '\n')


# Function to check proxy
def check_proxy(proxy, max_retries=5):
    if proxy == 'no_proxy':
        print("No proxy.")
        return 'no_proxy'
    retries = 0
    while retries < max_retries:
        try:
            ip, port, username, password = proxy.split(':')
            proxy_url = f'http://{username}:{password}@{ip}:{port}'
            print(f"Checking proxy: {proxy_url}")
            response = requests.get('http://api.ipify.org', proxies={'http': proxy_url, 'https': proxy_url}, timeout=30)
            response.raise_for_status()
            if response.text.strip() != ip:
                print(f"IP proxy ({response.text.strip()}) not matching ({ip}).")
                return proxy_url
            else:
                print(f"IP proxy {response.text.strip()} maching.")
                return proxy_url
        except requests.exceptions.RequestException as err:
            print(f"Proxy error: {err}")
            retries += 1
    print(f"Failed to check proxy after {max_retries} retries.")
    exit(1)

with open('accounts/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

print("Available accounts:")
accounts = list(config.keys())
for i, account in enumerate(accounts, 1):
    print(f"{i}. {account}")

print('-' * os.get_terminal_size().columns)

chosen_account = int(input("Choose account number:")) - 1
account = config[accounts[chosen_account]]

lock_file = create_lock_file(accounts[chosen_account])

session = requests.Session()
for cookie in account['cookies'][0]:
    session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'])

print(f"Chosen account: {Fore.LIGHTYELLOW_EX}{accounts[chosen_account]}{Style.RESET_ALL}")

proxy = account.get('proxy', 'no_proxy')
proxy_url = check_proxy(proxy)
if proxy_url is None:
    print("Proxy error.")
    exit(1)

if proxy != 'no_proxy':
    session.proxies = {'http': proxy_url, 'https': proxy_url}


if proxy_url is None:
    print("Proxy error.")
    exit(1)


url = "https://www.messenger.com"

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
}

response = session.get(url, headers=headers)


try:
    response_text = response.content.decode('utf-8')
except UnicodeDecodeError:
    print("Erro while decoding UTF-8.")

response_text = response_text.replace('\\\\', '\\')

import codecs

try:
    response_text = codecs.decode(response_text, 'unicode_escape')
except UnicodeEncodeError as e:
    print("UnicodeEncodeError:", str(e))
    start = max(0, e.start - 10)
    end = min(len(response_text), e.end + 10)
    print("Problematic data:", response_text[start:end])

data = response_text

matches = re.findall(r'entity_id=(\d+)&entity_type=10', data)



parser = argparse.ArgumentParser()
parser.add_argument("-m", "--message")
parser.add_argument("-r", "--recipient", type=int)
args = parser.parse_args()

response.raise_for_status()

inbox_html_page = response.text

dtsg = re.search(r'"DTSGInitialData",\[\],\{"token":"([^"]+)"', inbox_html_page).group(1)
device_id = re.search(r'"deviceId":"([^"]+)"', inbox_html_page).group(1)
schema_version = "4680497022042598"

script_urls = re.findall(r'src="([^"]+)"', inbox_html_page)
scripts = [session.get(url).text for url in script_urls if not url.startswith('data:')]

doc_id = next(re.search(r'id:"([0-9]+)",metadata:\{\},name:"LSPlatformGraphQLLightspeedRequestQuery"', script).group(1) for script in scripts if "LSPlatformGraphQLLightspeedRequestQuery" in script)

timestamp = int(datetime.datetime.now().timestamp() * 1000)

epoch = timestamp << 22
otid = epoch + random.randrange(2 ** 22)

if not os.path.exists('logs'):
    os.makedirs('logs')

account_folder = os.path.join('logs', accounts[chosen_account])
if not os.path.exists(account_folder):
    os.makedirs(account_folder)

logger = logging.getLogger('auto_responder')
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

log_file = os.path.join(account_folder, f'{datetime.datetime.now().strftime("%Y-%m-%d%H-%M-%S")}.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(levelname)s: [%(message)s]')
file_handler.setFormatter(formatter)


logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_and_print(*args, use_color=True):
    message = ' - '.join(map(str, args))
    message_no_color = re.sub(r'\x1b\[.*?m', '', message)
    logger.info(message_no_color)

messages = config[accounts[chosen_account]]['messages']

message = random.choice(messages)

num_replies = config[accounts[chosen_account]]['num_replies']
replies_sent = 0

for chat_id in matches:
    if replies_sent >= num_replies:
        log_and_print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Number of replies reached ({num_replies}). Exiting...")
        break
    if has_responded(accounts[chosen_account], chat_id):
        log_and_print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Chat {chat_id} has already been responded to. Skipping...")
        continue


    wait_time = random.uniform(600, 950)

    for _ in range(5):  # Try up to 5 times to send the message
        try:
            send_message_resp = session.post(
                "https://www.messenger.com/api/graphql/",
                data={
                    "fb_dtsg": dtsg,
                    "doc_id": doc_id,
                    "variables": json.dumps(
                        {
                            "deviceId": device_id,
                            "requestId": 0,
                            "requestPayload": json.dumps(
                                {
                                    "version_id": str(schema_version),
                                    "tasks": [
                                        {
                                            "label": "46",
                                            "payload": json.dumps(
                                                {
                                                    "thread_id": chat_id,
                                                    "otid": str(otid),
                                                    "source": 0,
                                                    "send_type": 1,
                                                    "text": message,
                                                    "initiating_source": 1,
                                                }
                                            ),
                                            "queue_name": str(chat_id),
                                            "task_id": 0,
                                            "failure_count": None,
                                        },
                                        {
                                            "label": "21",
                                            "payload": json.dumps(
                                                {
                                                    "thread_id": chat_id,
                                                    "last_read_watermark_ts": timestamp,
                                                    "sync_group": 1,
                                                }
                                            ),
                                            "queue_name": str(chat_id),
                                            "task_id": 1,
                                            "failure_count": None,
                                        },
                                    ],
                                    "epoch_id": epoch,
                                }
                            ),
                            "requestType": 3,
                        }
                    ),
                },
            )
            send_message_resp.raise_for_status()  # If status code is not 200, raise an exception
            break  # If the message was sent successfully, break out of the loop
        except (requests.exceptions.ProxyError, requests.exceptions.HTTPError):
            print("Proxy error or HTTP error. Waiting 5 seconds and trying again...")
            time.sleep(5)
    else:
        print("Failed to send message. Waiting 5 seconds and trying again...")
        continue 

    if send_message_resp.status_code == 200:
        mark_as_responded(accounts[chosen_account], chat_id)
        log_and_print(f"[{replies_sent+1}/{num_replies}] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Responded to user {chat_id}, waiting {wait_time} seconds, sent: {message}")
        time.sleep(wait_time)
        replies_sent += 1
    else:
        log_and_print(accounts[chosen_account], f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Failed to send message to {chat_id}. Status: {send_message_resp.status_code}")
        log_and_print(accounts[chosen_account], send_message_resp.text)
        time.sleep(random.uniform(5, 10))


    if random.random() < 0.8:
        message_index = messages.index(message)
        message = messages[(message_index + 1) % len(messages)]

log_and_print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: All done. Sent {replies_sent} replies.")

os.remove(lock_file)