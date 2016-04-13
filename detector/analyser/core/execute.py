from reader import Reader
from multiprocessing import *
from multiprocessing.sharedctypes import  Value
from multiprocessing.managers import BaseManager, SyncManager
from config import CoreConfigure, logging
from util import Node, Tree, InvertedIndex, DateTimeHashTable, HistroyRecord
import time
import signal
import os
from django.conf import settings
import json
logging.basicConfig(level = logging.INFO,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("detector")


class logProfiler(object):
    def __init__(self):
        self.reader = Reader()
        self.shareQueue = JoinableQueue()
        self.finalTreeCollection = Manager().Queue()
        self.processPool = []
        self.slaveNumber = 2
        self.count = Value('i',0)
        self.manager = Manager()
        self.sharedLst = self.manager.list()
        self.invertedIndex = InvertedIndex()
        self.services = {}
        self.final = []
        self.sessionid = None
        self.username = None
        self.datetime_str = None
    def run(self, data = None, username = None, datetime_str = None):
        '''
            data: filename_list
            sessionid: user_session_id
        '''
        self.username = username
        self.datetime_str = datetime_str

        logger.info("begin run")
        # start cpu_num - 1 work process to build call tree for each request
        begin = time.clock()
        # start up several processes
        self.startUp()
        # main process extract requset info and patch to slave process
        # in each slave process, build call tree, merge to the whole on, send the final tree to main process
        self.generate_task(data)
        # set barried
        self.clearUp()
        # merge for sub process
        self.gather()
        # insert all method to invertedindex
        self.export_request_flow()
        self.export_response_time()
        self.save_thread_info()
        self.saveToInvertedIndex()
        # calcu score
        self.invertedIndex.calcuScore()
        # all score to final tree and convert tree to json format
        self.addScoreTagAndToJson(username, datetime_str)
        self.addScoreTagAndToJson(username, "temp")
        # save execute info to file

        logger.info("total time elapsed" + str(time.clock() - begin))
        return self.final, self.invertedIndex.rankLst
    def addScoreTagAndToJson(self, username = None, datetime_str = None):
        for tree in self.final:
            tree.addScoreTagAndToJson(self.invertedIndex.rankLst, username, datetime_str)
    def saveToInvertedIndex(self):
        for itm in self.final:
            method_lst = itm.traverse()
            for methodElement in method_lst:
                self.invertedIndex.insert(methodElement, itm.serviceId)

    def slave(self, shareQueue, count, sharedLst, services, lock):
        logger.info(current_process())
        # obtain all request infomation
        while True:
            item = shareQueue.get()
            count.value = count.value + 1
            if item == 'Done':
                break
            else:
                # handle item
                tree = Tree(item['serviceId'], item['total_time'], item['datetime'], item['thread_name'])
                method_lst = item['method_lst']
                for method in method_lst:
                   tree.insert(Node(method))
                # the invalid means there exists some node its children execution time larger than the total time
                # discard the invalid tree
                if tree.check_validation() is False:
                    continue
                # tree hash
                tree.root.getHash()
                if item['serviceId'] in self.services.keys():
                    treeLst = self.services[item['serviceId']]
                    treeLst.append(tree)
                    self.services[item['serviceId']] = treeLst
                else:
                    treeLst = [tree]
                    self.services[item['serviceId']] = treeLst
            # create sub process to merge call tree
        self.startUpMerge()
        self.clearUp()
        # return to main process
        while self.finalTreeCollection.empty() is False:
            sharedLst.append(self.finalTreeCollection.get())

        logger.info("%s-%s" % (current_process(), "Done") )
    def mergeSlave(self, serviceData, queue):
        # select with same hashcode
        services = {}
        for item in serviceData:
            if item.root.hashcode in services.keys():
                services[item.root.hashcode].append(item)
            else:
                services[item.root.hashcode] = [item]
        # merge tree with same hashcode
        resLst = []
        for key,val in services.items():
            resTree = val[0]
            for itm in val[1:]:
                resTree.merge(itm)
            resLst.append(resTree)
        # merge tree with different hashcode
        finalTree = resLst[0]
        for itm in resLst[1:]:
            finalTree.mergeDifferent(itm)
        queue.put(finalTree)
    def check_validation(self, tree):
        total = 0
        for child in tree.root.children:
            total = total + child.percentageRoot
        if total < 0.95:
            return False
        else:
            return True
    def startUp(self):
        lock = Lock()
        for i in range(self.slaveNumber):
            self.processPool.append(Process(target = self.slave, args = (self.shareQueue, self.count, self.sharedLst, self.services, lock)))
        for process in self.processPool:
            process.start()
    def clearUp(self):
        for process in self.processPool:
            process.join()
        self.processPool = []
    def startUpMerge(self):
        self.processPool = []
        for i in self.services.keys():
            oneServiceData = self.services[i]
            self.processPool.append(Process(target = self.mergeSlave, args = (oneServiceData, self.finalTreeCollection)))
        for process in self.processPool:
            process.daemon = True
        for process in self.processPool:
            process.start()
    def generate_task(self, data):
        #logger.info("read data")
        for item in self.reader.execute(test_data = data):
            # add to shared queue
            self.shareQueue.put(item)
        #logger.info("read data finish")
        logger.info("total requests" + str(self.reader.count))
        # send finish msg
        for i in range(self.slaveNumber):
            self.shareQueue.put('Done')
    def gather(self):
        # classfify
        dic = {}
        for itm in self.sharedLst:
            if itm.serviceId in dic.keys():
                dic[itm.serviceId].append(itm)
            else:
                dic[itm.serviceId] = [itm]
        for service, trees in dic.items():
            tree = trees[0]
            for i in trees[1:]:
                tree.mergeDifferent(i)
            tree.calcuTreeAvg()
            tree.save_occur_time(self.username, self.datetime_str)
            # temp directory
            tree.save_occur_time(self.username, "temp")
            self.final.append(tree)
        logger.info("Service total: " + str(len(self.final)))
    def export_request_flow(self):
        # criteria by minute
        date_table =  DateTimeHashTable()
        for final_tree in self.final:
            for occur_date in final_tree.occurtime:
                date_table.insert(occur_date)
        date_lst =  date_table.export()
        date_table.save_to_file(date_lst, self.username, self.datetime_str)
        # temp directory
        date_table.save_to_file(date_lst, self.username, "temp")
    def export_response_time(self):
        for final_tree in self.final:
            final_tree.save_response_time(self.username, self.datetime_str)
            final_tree.save_response_time(self.username, "temp")
    def save_thread_info(self):
        _thread_info = {}
        for tree in self.final:
            for elem in tree.thread_info:
                thread_name = elem['thread_name']
                if thread_name in _thread_info.keys():
                    _thread_info[thread_name] += elem['total_time']
                else:
                    _thread_info[thread_name] = elem['total_time']
        user_directory = os.path.join(settings.JSON_ROOT, self.username)
        if not os.path.exists(user_directory):
            os.makedirs(user_directory)

        datetime_directory = os.path.join(user_directory, self.datetime_str)
        temp_directory = os.path.join(user_directory, "temp")
        # save to record directory
        if not os.path.exists(datetime_directory):
            os.makedirs(datetime_directory)
        # save to temp directory
        if not os.path.exists(temp_directory):
            os.makedirs(temp_directory)

        filename = datetime_directory + "/thread.json"
        try:
            f = open(filename, "w+")
            json.dump(_thread_info, f, indent = 2)
        except Exception, e:
            logger.error(e)
        finally:
            f.close()
if __name__ == "__main__":
    logprofiler = logProfiler()
    logprofiler.run(None, None)
