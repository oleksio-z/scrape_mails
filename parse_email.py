import asyncio
import aiohttp
import aiofiles
import argparse
from termcolor import colored
import re
import random


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0'
]

PROXIES = [
    #"http://proxy1.com:8080",
    # Add more proxies here...
    #"http://124.106.228.30:8080",
    #"https://67.213.212.12:62089",
    #"https://34.116.7.175:8080",
    #"https://146.190.218.26:12424",
    #"https://192.111.137.34:18765",
    #"https://217.25.24.7:3629",
    #"https://66.29.128.242:10229",
    #"https://192.141.232.12:33998",
    #"https://135.125.30.135:42625",
    #"https://122.129.107.54:5678",
    #"https://110.74.195.33:5678",
    #"https://38.127.179.219:46656",
    #"https://213.16.81.147:5678",
    #"https://27.131.168.137:5678",
    #"https://178.253.200.209:1080",
    #"https://145.239.2.102:40325",
    #"https://112.78.138.163:5678",
    #"https://43.153.108.126:443"
]

def main():
    usage = "Usage: python script.py [-m] [--max_connections] [-ct] [--connectio_attemts] [-t] [--timeout] input_filename output_filename"
    parser = argparse.ArgumentParser(usage=usage)

    parser.add_argument("-m", "--max_connections", default='50', type=int)
    parser.add_argument("-ct", "--connection_attempts", default='2', type=int)
    parser.add_argument("-t", "--timeout", default='5', type=int)
    parser.add_argument("input_filename")
    parser.add_argument("output_filename")
    args = parser.parse_args()

    asyncio.run(process_files(args.input_filename, args.output_filename, args.max_connections, args.timeout, args.connection_attempts))

async def process_files(input_file, output_file, limit, timeout, attempts):
    semaphore = asyncio.Semaphore(limit)
    tasks = []

    async with aiofiles.open(output_file, 'w') as outfile:
        async with aiofiles.open(input_file, 'r') as domains:
            async for domain in domains:
                async with semaphore:
                    tasks.append(asyncio.create_task(helper_func(outfile, domain, timeout, attempts)))

                    tasks = list(filter(lambda t: t and not t.done(), tasks))
                #tasks = [t for t in tasks if t and not t.done()]

            if tasks:
                await asyncio.gather(*tasks)

async def helper_func(outfile, domain, timeout, attempts):
    try:
        html = await fetch_html(domain, timeout, attempts)
        if html:
            mails = find_mail(html, domain)
            if mails:
                await outfile.write(f"{domain.strip()} , {mails}\n")
    except Exception as e:
        handle_errs(domain, e)
        return None

async def write_results(output_file, domain, mails):
    if mails:
        await output_file.write(f"{domain.strip()} , {mails}\n")

async def fetch_html(url, timeout, attempts):
    #proxy = random.choice(PROXIES)

    for i in range(attempts):
        user_agent = random.choice(USER_AGENTS)
        headers = {'User-Agent': user_agent}

        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=timeout), read_bufsize=2**16) as session: #trust_env=True
                try:
                    async with session.get(url.strip()) as response:    #proxy=proxy
                        if response.status == 200:
                            return await response.text()
                except Exception as e:
                    handle_errs(url)


#print(colored(f"[ERR] {url.strip()}, response status: {response.status}", "red"))

def find_mail(html, domain):
    emails = set()

    if html:
        try:
            email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
            emails.update(set(re.findall(email_pattern, html)))
            return emails
        except Exception as e:
            handle_errs(domain, e)
    else:
        handle_errs(domain)

def handle_errs(domain, e=''):
    print(colored(f"[ERR] {domain.strip()}, {str(e)}","red"))

if __name__ == '__main__':
    main()
