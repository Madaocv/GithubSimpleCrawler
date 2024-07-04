import requests
from bs4 import BeautifulSoup
from lxml import html
import time
import random
import json
from jsonschema import validate
import argparse

http = requests.Session()
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en,uk;q=0.9',
    'cache-control': 'max-age=0',
    'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
}


def convert_to_dict(row):
    keys = ['IP_Address', 'Port', 'Code', 'Country', 'Anonymity', 'Google', 'Https', 'Last_Checked']
    return dict(zip(keys, row))


def get_proxy_url(proxy):
    protocol = "http" if proxy['Https'] == 'no' else "https"
    return {protocol: f"{protocol}://{proxy['IP_Address']}:{proxy['Port']}"}


def parse_proxy_with_lxml():
    url = "https://free-proxy-list.net/"
    response = http.get(url, headers=headers)
    tree = html.fromstring(response.content)
    rows = tree.xpath('//table[@class="table table-striped table-bordered"]/tbody/tr')
    data = []
    for row in rows[:20]:
        cells = row.xpath('td')
        row_data = [cell.text_content() for cell in cells]
        data.append(row_data)
    return data


def get_random_proxy(proxies_list):
    proxy = random.choice(proxies_list)
    proxy_url = f"http://{proxy['IP_Address']}:{proxy['Port']}"
    if proxy['Https'] == 'yes':
        return {'http': proxy_url, 'https': proxy_url}
    else:
        return {'http': proxy_url}


def fetch_with_retries(url, proxies_list, retries=15, backoff_factor=2):
    for attempt in range(retries):
        proxy_url = get_random_proxy(proxies_list)
        try:
            response = http.get(url, proxies=proxy_url, headers=headers, timeout=5)
            response.raise_for_status()
            print(proxy_url)
            return response, proxy_url
        except Exception as e:
            print("*" * 50)
            print(f"Attempt {attempt + 1} failed: {e}")
            print(proxy_url)
            print("*" * 50)
            time.sleep(backoff_factor)
    return None, None


def get_details(url, proxy_url):
    print("Getting details from URL: " + url)
    prefix = 'https://github.com/'
    url_without_prefix = url[len(prefix):]
    path_parts = url_without_prefix.split('/')
    username = path_parts[0]

    detail_response = http.get(url, proxies=proxy_url, headers=headers)
    soup = BeautifulSoup(detail_response.text, 'html.parser')
    language_stats = {}
    try:
        h2_tag = soup.find('h2', string='Languages')
        parent_div = h2_tag.find_parent('div')
        languages = parent_div.find_all('a')

        for lang in languages:
            language_name = lang.find('span', attrs={'class': True}).text.strip()
            percentage = lang.find('span', attrs={'class': False}).text.strip()
            language_stats.update({language_name: float(percentage.replace('%', ''))})
    except Exception as e:
        print(f"Can not detect Languages: {str(e)}")

    out_dict = {
        "url": url,
        "extra": {
            "owner": username,
        }
    }
    if language_stats:
        out_dict["extra"]["language_stats"] = language_stats
    return out_dict


def load_schema(schema_path):
    """Load the JSON schema at the given path as a Python object.
    Args:
        schema_path: A filename for a JSON schema.
    Returns:
        A Python object representation of the schema.
    """
    try:
        with open(schema_path) as schema_file:
            schema = json.load(schema_file)
    except ValueError as e:
        print('Invalid JSON in schema or included schema: {}\n{}'.format(schema_file.name, str(e)))
    return schema


def main(inputkeywords=None, search_type='Repositories'):
    git_main_page_url = f"https://github.com/search?q={'+'.join(inputkeywords)}&type={search_type.lower()}"
    print('Main page: ', git_main_page_url)
    proxies_list = parse_proxy_with_lxml()
    dict_list_proxies = [convert_to_dict(row) for row in proxies_list]
    response, successful_proxy = fetch_with_retries(git_main_page_url, dict_list_proxies)
    output_file = []
    if response:
        print('Main page response.status_code: ', response.status_code)
        soup = BeautifulSoup(response.text, 'html.parser')
        for obj in soup.find("div", {"data-testid": "results-list"}).find_all("h3"):
            detail_url = f'https://github.com{obj.a.get("href")}'
            output_file.append(get_details(detail_url, successful_proxy))
    else:
        print("Failed to fetch the URL.")
    validate(instance=output_file, schema=load_schema("schema.json"))
    with open(f'outputfile_{"_".join(inputkeywords)}.json', 'w') as file:
        file.write(json.dumps(output_file, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GitHub Crawler')
    parser.add_argument('keywords', type=str, nargs='+', help='Search keywords')
    parser.add_argument('--type', type=str, default='Repositories', help='The type of object to search for (Wiki, Issues, Repositories)')
    args = parser.parse_args()
    main(inputkeywords=args.keywords, search_type=args.type)
