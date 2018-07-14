# -*- coding: utf-8 -*-
# @File    : selenium.py
# @Author  : LVFANGFANG
# @Time    : 2018/7/14 0014 14:35
# @Desc    :

import logging
import platform
from urllib.request import _parse_proxy

from pyvirtualdisplay import Display
from scrapy import signals
from scrapy.http import HtmlResponse
from selenium import webdriver

from .extension import create_proxyauth_extension

logger = logging.getLogger(__name__)


class SeleniumMiddleware:
    """Scrapy middleware handling the requests using selenium"""

    def __init__(self, proxy_url=None):

        options = webdriver.ChromeOptions()
        # disable images
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2
            }
        }
        options.add_experimental_option('prefs', prefs)

        if proxy_url:
            proxy_type, user, password, hostport = _parse_proxy(proxy_url)
            proxyauth_plugin_path = create_proxyauth_extension(
                proxy_host=hostport.split(':')[0],
                proxy_port=hostport.split(':')[1],
                proxy_username=user,
                proxy_password=password,
                scheme=proxy_type,
                plugin_path="vimm_chrome_proxyauth_plugin.zip"
            )
            options.add_extension(proxyauth_plugin_path)

        self.display = self.get_display()

        self.driver = webdriver.Chrome(chrome_options=options)
        self.driver.set_page_load_timeout(30)

    @classmethod
    def from_crawler(cls, crawler):

        proxy_url = crawler.settings.get('PROXY_URL', None)
        s = cls(proxy_url=proxy_url)
        crawler.signals.connect(s.spider_closed, signals.spider_closed)
        return s

    def process_request(self, request, spider):

        self.driver.get(request.url)

        script = '''
            var delay = 10;
            var scroll_amount = 50;
            var interval = setInterval(function scroller() {
                var old = document.documentElement.scrollTop;
                window.scrollTo(0,old+scroll_amount);
                if (document.documentElement.scrollTop == old) {
                    clearInterval(interval);
                }
            },delay);
        '''
        self.driver.execute_script(script)

        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie(
                {
                    'name': cookie_name,
                    'value': cookie_value
                }
            )

        body = str.encode(self.driver.page_source)

        return HtmlResponse(
            self.driver.current_url,
            body=body,
            encoding='utf-8',
            request=request
        )

    def spider_closed(self):
        try:
            if self.driver:
                self.driver.delete_all_cookies()
                self.driver.quit()
        except Exception as e:
            logger.exception(e)

        try:
            self.display and self.display.stop()
        except Exception as e:
            logger.exception(e)

    def get_display(self):
        if platform.system() != 'Windows':
            display = Display(visible=0, size=(1024, 768))
            display.start()
        else:
            display = None
        return display
