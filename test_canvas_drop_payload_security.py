import unittest
from urllib.parse import quote

from CanvasDropPayload import _host_is_or_subdomain, _unwrap_image_search_url


class CanvasDropPayloadSecurityTests(unittest.TestCase):
    def test_host_is_or_subdomain_accepts_exact_and_real_subdomain(self):
        self.assertTrue(_host_is_or_subdomain('bing.com', 'bing.com'))
        self.assertTrue(_host_is_or_subdomain('www.bing.com', 'bing.com'))
        self.assertTrue(_host_is_or_subdomain('images.bing.com.', 'bing.com'))

    def test_host_is_or_subdomain_rejects_substring_spoofs(self):
        self.assertFalse(_host_is_or_subdomain('notbing.com', 'bing.com'))
        self.assertFalse(_host_is_or_subdomain('bing.com.evil.example', 'bing.com'))
        self.assertFalse(_host_is_or_subdomain('evil.example', 'bing.com'))

    def test_bing_wrapper_unwraps_on_trusted_hostname(self):
        target = 'https://images.example/cat.png'
        wrapper = 'https://www.bing.com/images/search?mediaurl=' + quote(target, safe='')
        self.assertEqual(_unwrap_image_search_url(wrapper), target)

    def test_bing_text_in_path_does_not_unwrap(self):
        target = 'https://images.example/cat.png'
        wrapper = 'https://evil.example/path/bing.com?mediaurl=' + quote(target, safe='')
        self.assertEqual(_unwrap_image_search_url(wrapper), wrapper)

    def test_bing_spoofed_hostname_does_not_unwrap(self):
        target = 'https://images.example/cat.png'
        wrapper = 'https://bing.com.evil.example/?mediaurl=' + quote(target, safe='')
        self.assertEqual(_unwrap_image_search_url(wrapper), wrapper)

    def test_google_substring_spoof_does_not_unwrap(self):
        target = 'https://images.example/cat.png'
        wrapper = 'https://evilgoogle.com/search?imgurl=' + quote(target, safe='')
        self.assertEqual(_unwrap_image_search_url(wrapper), wrapper)


if __name__ == '__main__':
    unittest.main()
