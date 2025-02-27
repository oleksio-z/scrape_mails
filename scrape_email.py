import asyncio
import aiohttp
import aiofiles
import argparse
from termcolor import colored
import re
import random
from urllib.parse import urlparse, urljoin

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

def main():
    usage = "Usage: python script.py [-m] [--max_connections] [-ct] [--connection_attempts] [-t] [--timeout] [-d] [--deepness] input_filename output_filename"
    parser = argparse.ArgumentParser(usage=usage)

    parser.add_argument("-m", "--max_connections", default=50, type=int)
    parser.add_argument("-ct", "--connection_attempts", default=2, type=int)
    parser.add_argument("-t", "--timeout", default=5, type=int)
    parser.add_argument("-d", "--deepness", default=1, type=int, help="Depth of link-following")
    parser.add_argument("input_filename")
    parser.add_argument("output_filename")
    args = parser.parse_args()

    asyncio.run(process_files(args.input_filename, args.output_filename, args.max_connections, args.timeout, args.connection_attempts, args.deepness))

async def process_files(input_file, output_file, limit, timeout, attempts, deepness):
    semaphore = asyncio.Semaphore(limit)
    tasks = []

    async with aiofiles.open(output_file, 'w') as outfile:
        async with aiofiles.open(input_file, 'r') as domains:
            async for domain in domains:
                domain = domain.strip()
                async with semaphore:
                    tasks.append(asyncio.create_task(traverse_website(outfile, domain, timeout, attempts, deepness)))
                    tasks = list(filter(lambda t: t and not t.done(), tasks))
            if tasks:
                await asyncio.gather(*tasks)

async def traverse_website(outfile, domain, timeout, attempts, deepness):
    parsed_domain = urlparse(domain).netloc
    found_emails = set()

    async def crawl(url, current_depth):
        if current_depth > deepness:
            return
        html = await fetch_html(url, timeout, attempts)
        if html:
            found_emails.update(find_mail(html, parsed_domain))

            if current_depth < deepness:
                links = find_links(html, parsed_domain, url)
                for link in links:
                    await crawl(link, current_depth + 1)

    await crawl(domain, 1)
    if found_emails:
        await outfile.write(f"{parsed_domain}: {', '.join(found_emails)}\n")

async def fetch_html(url, timeout, attempts):
    for i in range(attempts):
        user_agent = random.choice(USER_AGENTS)
        headers = {'User-Agent': user_agent}

        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception as e:
                handle_errs(url, e)
    return None

def find_mail(html, domain):
    emails = set()
    try:
        email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?!png|jpg|jpeg|gif|bmp|tiff|webp|svg|ico|woff2)\b[A-Z|a-z]{2,}\b'
        )
        emails.update(re.findall(email_pattern, html))
    except Exception as e:
        handle_errs(domain, e)
    return emails


def find_links(html, domain, base_url):
    links = set()
    try:
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        for match in href_pattern.findall(html):
            full_url = urljoin(base_url, match)
            parsed_url = urlparse(full_url)
            if parsed_url.netloc == domain and not full_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.woff2')):
                links.add(full_url)
    except Exception as e:
        handle_errs(domain, e)
    return links

def handle_errs(domain, e=''):
    print(colored(f"[ERR] {domain.strip()}, {str(e)}", "red"))

if __name__ == '__main__':
    main()
