# coding:utf-8
import logging
from config import CoreConfigure
logging.basicConfig(level = logging.INFO,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("util")
class UrlObj(object):
    def __init__(self, url = None, depth = 0, type = 0, package_name = None, class_name = None, method_name = None):
        # depth可以用来控制爬虫的深度
        self.url = url.strip("/")
        self.depth = depth
        '''
            customize different url type which judge by greenlet handle
            type:
            0 : root
            1 : class page
            2 : method page
        '''
        self.type = type
        self.package_name = package_name
        self.class_name = class_name
        self.method_name = method_name
    def __str__(self):
        return self.url
    def __repr(self):
        return "<url_object :%s>" % self.url
    def __hash__(self):
        return hash(self.url)

class UrlTable(object):
    def __init__(self, size = None):
        self.__urls = {}
        if size:
            self.size = size
        else:
            size = float("inf")
    def __len__(self):
        return len(self.__urls)
    def __contains__(self, url):
        return hash(url) in self.__urls.keys()
    def __iter__(self):
        for url in self.urls:
            yield url
    @property
    def urls(self):
        return self.__urls.values()
    def is_full(self):
        return len(self) >= self.size
    def insert(self, url):
        if isinstance(url, basestring):
            url = UrlObj(url)
        if url not in self:
            self.__urls.setdefault(hash(url), url)


if __name__ == "__main__":
    logger.info("Test");


