from reader import Reader
from multiprocessing import *
from multiprocessing.sharedctypes import  Value
from multiprocessing.managers import BaseManager, SyncManager
from config import CoreConfigure, logging
from util import Node, Tree, InvertedIndex
import time
import signal
import os
from django.conf import settings
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
    def run(self, data = None, sessionid = None):
        '''
            data: filename_list
            sessionid: user_session_id
        '''
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
        self.saveToInvertedIndex()
        # calcu score
        self.invertedIndex.calcuScore()
        # all score to final tree and convert tree to json format
        self.addScoreTagAndToJson(sessionid)
        logger.info("total time elapsed" + str(time.clock() - begin))
        return self.final, self.invertedIndex.rankLst
    def addScoreTagAndToJson(self, sessionid = None):
        for tree in self.final:
            tree.addScoreTagAndToJson(self.invertedIndex.rankLst, sessionid)
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
                tree = Tree(item['serviceId'], item['total_time'])
                method_lst = item['method_lst']
                for method in method_lst:
                    tree.insert(Node(method))
                # tree hash
                tree.check_validation()
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
    def generate_task(self, test_data):
        #logger.info("read data")
        for item in self.reader.execute(test_data):
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
            #logger.debug("tree check validation")
            #tree.checkIsValid()
            #logger.debug("final tree : \n" + tree.__repr__())
            self.final.append(tree)
        logger.info("Service total: " + str(len(self.final)))
if __name__ == "__main__":
    logprofiler = logProfiler()
    logprofiler.run(None, None)
