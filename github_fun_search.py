import requests
from bs4 import BeautifulSoup
from lxml import html
import random
import json
import time
import re
from jsonschema import validate
import argparse
import sys
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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


def validate_proxy(proxy):
    proxy_pattern = re.compile(r'^(http|https)://\d+\.\d+\.\d+\.\d+:\d+$')
    if not proxy_pattern.match(proxy):
        raise argparse.ArgumentTypeError(f"Invalid proxy format: {proxy}")
    return proxy


def validate_filename(filename):
    if not filename:
        raise argparse.ArgumentTypeError("Filename cannot be empty")
    return filename


def convert_to_dict(row):
    keys = ['IP_Address', 'Port', 'Code', 'Country', 'Anonymity', 'Google', 'Https', 'Last_Checked']
    return dict(zip(keys, row))


def get_proxy_url(proxy):
    protocol = "http" if proxy['Https'] == 'no' else "https"
    return {protocol: f"{protocol}://{proxy['IP_Address']}:{proxy['Port']}"}


def get_proxy_url_string(proxy_url):
    protocol, address = proxy_url.split("://")
    ip_address, port = address.split(":")
    return {protocol: f"{protocol}://{ip_address}:{port}"}


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
    if proxy.get('Https', '') == 'yes':
        return {'http': proxy_url, 'https': proxy_url}
    else:
        return {'http': proxy_url}


def fetch_with_retries(url, proxies_list, retries=15, backoff_factor=2, explicit_proxy=None):
    for attempt in range(retries):
        proxy_url = get_proxy_url_string(explicit_proxy) if explicit_proxy else get_random_proxy(proxies_list)
        try:
            response = http.get(url, proxies=proxy_url, headers=headers, timeout=5)
            response.raise_for_status()
            logger.info(f"Selected proxy: {proxy_url}")
            return response, proxy_url
        except requests.exceptions.RequestException:
            ex_type, ex_value, ex_traceback = sys.exc_info()
            trace_back = traceback.extract_tb(ex_traceback)
            stack_trace = list()
            for trace in trace_back:
                stack_trace.append(f"File : {trace[0]} , Line : {trace[1]}, Func.Name : {trace[2]}, Message : {trace[3]}" )
            logger.error(f"Exception type : {ex_type.__name__}")
            logger.error(f"Exception message : {ex_value}")
            logger.error(f"Stack trace : {stack_trace}")
            logger.error(f"Proxy :{proxy_url}")
        time.sleep(backoff_factor)
    return None, proxy_url


def get_details(url, proxy_url):
    logger.info(f"Getting details from URL: {url}" )
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
    except AttributeError as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        trace_back = traceback.extract_tb(ex_traceback)
        stack_trace = list()
        for trace in trace_back:
            stack_trace.append(f"File : {trace[0]} , Line : {trace[1]}, Func.Name : {trace[2]}, Message : {trace[3]}" )
        logger.error(f"Exception type : {ex_type.__name__}")
        logger.error(f"Exception message : {ex_value}")
        logger.error(f"Stack trace : {stack_trace}")
        logger.error(f"Can not detect Languages: {str(e)}")

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
        logger.error('Invalid JSON in schema or included schema: {}\n{}'.format(schema_file.name, str(e)))
    return schema


def main(outputfilename=None, explicit_proxy=None):
    with open("inputfile.json") as json_file:
        json_data_inputfile = json.load(json_file)
    validate(instance=json_data_inputfile, schema=load_schema("shema_input.json"))
    git_main_page_url = f"https://github.com/search?q={'+'.join(json_data_inputfile['keywords'])}&type={json_data_inputfile['type'].lower()}"
    logger.info(f'Main page: {git_main_page_url}')
    proxies_list = parse_proxy_with_lxml()
    dict_list_proxies = [convert_to_dict(row) for row in proxies_list]
    dict_list_proxies.extend([{'IP_Address': obj.split(':')[0], 'Port': obj.split(':')[1]} for obj in json_data_inputfile['proxies']])
    response, successful_proxy = fetch_with_retries(git_main_page_url, dict_list_proxies, explicit_proxy=explicit_proxy)
    output_file = []
    if response:
        logger.info(f'Main page response.status_code: {response.status_code}')
        soup = BeautifulSoup(response.text, 'html.parser')
        detail_urls = [f'https://github.com{obj.a.get("href")}' for obj in soup.find("div", {"data-testid": "results-list"}).find_all("h3")]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_details, url, successful_proxy) for url in detail_urls]
            for future in as_completed(futures):
                output_file.append(future.result())

        validate(instance=output_file, schema=load_schema("schema_output.json"))
        if not outputfilename:
            outputfilename = "_".join(json_data_inputfile.get('keywords', 'Where is the keywords?'))
        with open(f'{outputfilename}.json', 'w') as file:
            file.write(json.dumps(output_file, indent=4))
    else:
        logger.error("Failed to fetch the URL.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GitHub Crawler')
    parser.add_argument('--proxy', type=validate_proxy, help='Proxy to use for requests')
    parser.add_argument('--filename', type=validate_filename, help='Filename for output')
    args = parser.parse_args()
    try:
        main(outputfilename=args.filename, explicit_proxy=args.proxy)
    except argparse.ArgumentTypeError as e:
        logger.error(e)
        sys.exit(1)
