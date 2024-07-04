import unittest
from unittest.mock import patch, Mock
import github_fun_search
import requests


class TestGithubFunSearch(unittest.TestCase):

    @patch('github_fun_search.http.get')
    def test_parse_proxy_with_lxml(self, mock_get):
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <table class="table table-striped table-bordered">
                    <tbody>
                        <tr><td>8.219.97.248</td><td>80</td><td>SG</td><td class="hm">Singapore</td><td>anonymous</td><td class="hm">no</td><td class="hx">yes</td><td class="hm">5 secs ago</td></tr>
                        <tr><td>111.247.40.246</td><td>80</td><td>TW</td><td class="hm">Taiwan</td><td>anonymous</td><td class="hm">no</td><td class="hx">no</td><td class="hm">5 secs ago</td></tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        proxies = github_fun_search.parse_proxy_with_lxml()
        self.assertEqual(len(proxies), 2)
        self.assertEqual(proxies[0][0], '8.219.97.248')

    @patch('github_fun_search.http.get')
    def test_get_details(self, mock_get):
        mock_response = Mock()
        mock_response.text = """
        <html>
            <body>
                <div class="BorderGrid-cell">
                                <h2 class="h4 mb-3">Languages</h2>
                <div class="mb-2">
                <span data-view-component="true" class="Progress">
                    <span style="background-color:#3572A5 !important;;width: 98.0%;" itemprop="keywords" aria-label="Python 98.0" data-view-component="true" class="Progress-item color-bg-success-emphasis"></span>
                    <span style="background-color:#e34c26 !important;;width: 1.1%;" itemprop="keywords" aria-label="HTML 1.1" data-view-component="true" class="Progress-item color-bg-success-emphasis"></span>
                    <span style="background-color:#384d54 !important;;width: 0.9%;" itemprop="keywords" aria-label="Dockerfile 0.9" data-view-component="true" class="Progress-item color-bg-success-emphasis"></span>
                </span></div>
                <ul class="list-style-none">
                    <li class="d-inline">
                        <a class="d-inline-flex flex-items-center flex-nowrap Link--secondary no-underline text-small mr-3" href="/cosmos-sajal/django_boilerplate/search?l=python" data-ga-click="Repository, language stats search click, location:repo overview">
                        <svg style="color:#3572A5;" aria-hidden="true" height="16" viewBox="0 0 16 16" version="1.1" width="16" data-view-component="true" class="octicon octicon-dot-fill mr-2">
                    <path d="M8 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z"></path>
                </svg>
                        <span class="color-fg-default text-bold mr-1">Python</span>
                        <span>98.0%</span>
                        </a>
                    </li>
                    <li class="d-inline">
                        <a class="d-inline-flex flex-items-center flex-nowrap Link--secondary no-underline text-small mr-3" href="/cosmos-sajal/django_boilerplate/search?l=html" data-ga-click="Repository, language stats search click, location:repo overview">
                        <svg style="color:#e34c26;" aria-hidden="true" height="16" viewBox="0 0 16 16" version="1.1" width="16" data-view-component="true" class="octicon octicon-dot-fill mr-2">
                    <path d="M8 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z"></path>
                </svg>
                        <span class="color-fg-default text-bold mr-1">HTML</span>
                        <span>1.1%</span>
                        </a>
                    </li>
                    <li class="d-inline">
                        <a class="d-inline-flex flex-items-center flex-nowrap Link--secondary no-underline text-small mr-3" href="/cosmos-sajal/django_boilerplate/search?l=dockerfile" data-ga-click="Repository, language stats search click, location:repo overview">
                        <svg style="color:#384d54;" aria-hidden="true" height="16" viewBox="0 0 16 16" version="1.1" width="16" data-view-component="true" class="octicon octicon-dot-fill mr-2">
                    <path d="M8 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z"></path>
                </svg>
                        <span class="color-fg-default text-bold mr-1">Dockerfile</span>
                        <span>0.9%</span>
                        </a>
                    </li>
                </ul>

                            </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        details = github_fun_search.get_details('https://github.com/owner/repo', {'http': 'http://8.8.8.8:80'})
        self.assertEqual(details['extra']['owner'], 'owner')
        self.assertEqual(details['extra']['language_stats']['Python'], 98.0)
        self.assertEqual(details['extra']['language_stats']['HTML'], 1.1)

    @patch('github_fun_search.http.get')
    def test_fetch_with_retries(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_get.return_value = mock_response
        proxies_list = [{'IP_Address': '8.8.8.8', 'Port': '80', 'Https': 'yes'}]
        response, proxy_url = github_fun_search.fetch_with_retries('http://example.com', proxies_list)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(proxy_url)


    @patch('github_fun_search.http.get')
    def test_main(self, mock_get):
        mock_proxy_response = Mock()
        mock_proxy_response.status_code = 200
        mock_proxy_response.content = b"""
        <table class="table table-striped table-bordered">
            <tbody>
                <tr><td>8.8.8.8</td><td>80</td><td></td><td></td><td></td><td></td><td>yes</td><td></td></tr>
                <tr><td>8.8.4.4</td><td>80</td><td></td><td></td><td></td><td></td><td>yes</td><td></td></tr>
            </tbody>
        </table>
        """
        mock_get.side_effect = [mock_proxy_response, mock_proxy_response]

        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.text = """
        <html>
            <body>
                <div data-testid="results-list">
                    <h3><a href="/owner/repo"></a></h3>
                </div>
            </body>
        </html>
        """
        mock_get.side_effect = [mock_proxy_response, mock_search_response]

        with patch('github_fun_search.get_details', return_value={
            'url': 'https://github.com/owner/repo',
            'extra': {'owner': 'owner', 'language_stats': {'Python': 97.1}}
        }):
            github_fun_search.main(inputkeywords=['python', 'django-rest-framework', 'jwt'])

    @patch('github_fun_search.http.get')
    def test_get_details_no_languages(self, mock_get):
        mock_response = Mock()
        mock_response.text = """
        <html>
            <body>
                <div class="BorderGrid-cell"></div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        details = github_fun_search.get_details('https://github.com/owner/repo', {'http': 'http://8.8.8.8:80'})
        self.assertEqual(details['extra']['owner'], 'owner')
        self.assertNotIn('language_stats', details['extra'])

    def test_convert_to_dict(self):
        row = ['8.8.8.8', '80', 'US', 'United States', 'anonymous', 'yes', 'yes', '5 mins ago']
        expected_dict = {
            'IP_Address': '8.8.8.8',
            'Port': '80',
            'Code': 'US',
            'Country': 'United States',
            'Anonymity': 'anonymous',
            'Google': 'yes',
            'Https': 'yes',
            'Last_Checked': '5 mins ago'
        }
        self.assertEqual(github_fun_search.convert_to_dict(row), expected_dict)

    @patch('github_fun_search.http.get')
    @patch('github_fun_search.time.sleep', return_value=None)
    def test_fetch_with_retries_fail(self, mock_sleep, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Simulated request failure")
        proxies_list = [{'IP_Address': '8.8.8.8', 'Port': '80', 'Https': 'yes'}]
        response, proxy_url = github_fun_search.fetch_with_retries('http://example.com', proxies_list, retries=1, backoff_factor=0)
        self.assertIsNone(response)
        self.assertIsNone(proxy_url)

    def test_convert_to_dict(self):
        row = ['8.8.8.8', '80', 'US', 'United States', 'elite proxy', 'no', 'yes', '0 seconds ago']
        proxy_dict = github_fun_search.convert_to_dict(row)
        self.assertEqual(proxy_dict['IP_Address'], '8.8.8.8')
        self.assertEqual(proxy_dict['Port'], '80')

    def test_get_proxy_url(self):
        proxy = {'IP_Address': '8.8.8.8', 'Port': '80', 'Https': 'yes'}
        proxy_url = github_fun_search.get_proxy_url(proxy)
        self.assertEqual(proxy_url, {'https': 'https://8.8.8.8:80'})
        
if __name__ == '__main__':
    unittest.main()
