from util import UrlObj, UrlTable
import gevent
from gevent import monkey, queue, event, pool
from pyquery import PyQuery
import requests
import logging
from threading import Timer
from datetime import datetime
from config import CoreConfigure
import os
import multiprocessing
import time
from pymongo import MongoClient
logging.basicConfig(level = logging.DEBUG,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("spider")

class Spider(object):
    def __init__(self):
        monkey.patch_all()
        self.queue = queue.Queue()
        self.pool = pool.Pool(int(CoreConfigure().get_config_section_map("spider")['concurrency']))
        self.url_table = UrlTable()
        self.timer = Timer(int(CoreConfigure().get_config_section_map("spider")['timeout']), self.stop)
        self._stop = event.Event()
        self.greenlet_finished = event.Event()
        self.root = None  # url_object
        self.initialize_db()
    def initialize_db(self):
        host = CoreConfigure().get_config_section_map('db')['host']
        port = CoreConfigure().get_config_section_map('db')['port']
        db_name = CoreConfigure().get_config_section_map('db')['database']
        collect_name = CoreConfigure().get_config_section_map('db')['collection']
        self.db_cli = MongoClient(host, int(port))
        # mongodb collection
        self.collection = self.db_cli[db_name][collect_name]
    def set_root(self, url):
        if isinstance(url, basestring):
            url = UrlObj(url, type = 0)
            self.root = url
        self.push_task(self.root)
        self.url_table.insert(self.root)

    def push_task(self, url):
        # type(url) is UrlObj
        if url not in self.url_table:
            self.queue.put(url)
    def run(self, url = None):
        begin = time.time()
        if url is None:
            # read from configure file for default value
            url = CoreConfigure().get_config_section_map('content')['root_url']
        self.set_root(url)
        self.timer.start()
        logger.info("spider begin crawl")
        while not self.stopped() and self.timer.isAlive():
            for greenlet in list(self.pool):
                if greenlet.dead:
                    self.pool.discard(greenlet)
            try:
                url = self.queue.get_nowait()
            except queue.Empty:
                if self.pool.free_count() != self.pool.size:
                    # wait until one greenlet finish to flash queue
                    self.greenlet_finished.wait()
                    self.greenlet_finished.clear()
                    continue
                else:
                    self.stop()
            greenlet = Handler(url, self)
            self.pool.start(greenlet)
        logger.info("total time elapsed %0.2f" % (time.time() - begin))
    def stopped(self):
        return self._stop.is_set()

    def stop(self):
        logger.info("spider finish, totally catched (%d) urls" % len(self.url_table))
        self.timer.cancel()
        self._stop.set()
        self.pool.join()
        self.queue.put(StopIteration)

class Handler(gevent.Greenlet):
    def __init__(self, url_object ,spider):
        gevent.Greenlet.__init__(self)
        self.url_object = url_object
        self.spider = spider
    def _run(self):
        # get all package link
        if self.url_object.type is 0:
            self.get_packages()
        elif self.url_object.type is 1:
            self.get_classes()
        else:
            self.get_methods()

        self.stop()

    def get_packages(self):
        response = requests.get(self.url_object.url)
        html_packages = PyQuery(response.text)
        all_a_element = html_packages("a")
        all_a_package_element = [package for package in all_a_element if isinstance(package.text, basestring) and package.text.startswith("java.")]
        # add all class href to queue
        for package_element in all_a_package_element:
            absolute_url = os.path.join(CoreConfigure().get_config_section_map("content")['package_root'], package_element.attrib['href'])
            url_object = UrlObj(absolute_url, type = 1, package_name = package_element.text, class_name = None, method_name = None)
            self.spider.queue.put(url_object)
    def get_classes(self):
        response = requests.get(self.url_object.url)
        html_classes = PyQuery(response.text)
        blocks = [PyQuery(b) for b in html_classes('li.blockList')]
        class_block = None
        for b in blocks:
            spans = b('span')
            for span in spans:
                if span.text == "Class Summary":
                    class_block = b
        if class_block is None:
            logger.info("no class found in %s" % self.url_object.url)
            return
        base = CoreConfigure().get_config_section_map('content')['class_root']
        for cls in class_block('td.colFirst a'):
            cls_name = cls.text
            cls_link = cls.attrib['href']
            cls_link = self.assemble_url(self.url_object.url, cls_link)
            url_object = UrlObj(cls_link, type = 2, package_name = self.url_object.package_name, class_name = cls_name, method_name = None)
            self.spider.queue.put(url_object)
    def get_methods(self):
        # get constructor
        response = requests.get(self.url_object.url)
        html_methods = PyQuery(response.text)

        block_lists = [PyQuery(block) for block in html_methods('li.blockList')]

        constructor_block = None
        method_block = None
        # filter to find two blocks define above
        for block in block_lists:
            a_list = block('a')
            for a in a_list:
                try:
                    if a.attrib['name'] == 'constructor_detail':
                        constructor_block = block
                    if a.attrib['name'] == 'method_detail':
                        method_block = block
                except:
                    pass
        # avoid first name
        if constructor_block:
            for link in constructor_block('a')[1:]:
                try:
                    method_line = link.attrib['name']
                    method_info = self.extra_method_info(method_line)
                    #  write to mongoDB
                    self.save_to_db(method_info)
                    self.spider.url_table.insert(self.url_object.url)
                except:
                    pass
        if method_block:
            for link in method_block('a')[1:]:
                try:
                    method_line = link.attrib['name']
                    method_info = self.extra_method_info(method_line)
                    # save to mongo
                    self.save_to_db(method_info)
                    self.spider.url_table.insert(self.url_object.url)
                except:
                    pass
    def extra_method_info(self, line):
        parameter_begin = line.find("(")
        method_name = line[:parameter_begin]
        parameter = line[parameter_begin + 1 : -1]
        parameter_list = parameter.split(", ")
        method_info = {}
        method_info['package_name'] = self.url_object.package_name
        method_info['class_name'] = self.url_object.class_name
        method_info['method_name'] = method_name
        method_info['parameters'] = parameter_list
        return method_info

    def assemble_url(self, base, extend):
        extend_list = extend.split("/")
        base_list = base.split("/")
        up_level = len([_ for _ in extend_list if _ == ".."])
        new_list = base_list[: len(base_list) - up_level - 1] + extend_list[up_level : ]
        return ("/").join(new_list)

    def save_to_db(self, method_dictionary):
        package = method_dictionary['package_name']
        class_ = method_dictionary['class_name']
        method = method_dictionary['method_name']
        full_method = (".").join([package, class_, method])
        self.spider.collection.insert_one({'method' : full_method})
    def stop(self):
        self.spider.greenlet_finished.set()
        self.kill(block = False)


class Execute(object):
    def __init__(self):
        self.spider = Spider()
    def crawl(self):
        # TODO modify to multiprocess and use backend database queue Redis
        self.spider.run()

def unittest():
    execute = Execute()
    execute.crawl()
    execute.spider.collection.insert_one({"lalla":1})
if __name__ == "__main__":
    unittest()

