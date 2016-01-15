import hashlib
import math
import json
from config import CoreConfigure, logging
import os
from django.conf import settings

logging.basicConfig(level = logging.DEBUG,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("util")
class Node:
    def __init__(self, info):
        self.methodName = info['name']
        self.executeTime = info['execute_time']
        self.position = info['position']
        self.p_Father = 0
        self.p_Root = 0
        self.children = []
        self.father = None
        self.depth = 0
        self.isValid = False
        self.hashcode = None
        self.maxTime = info['execute_time']
        self.minTime = info['execute_time']
        self.avgTime = info['execute_time']
        self.cnt = 1
        self.score = None
    @property
    def percentageFather(self):
        return self.p_Father
    @percentageFather.setter
    def percentageFather(self, percentage):
        self.p_Father = percentage

    @property
    def percentageRoot(self):
        return self.p_Root
    @percentageRoot.setter
    def percentageFather(self, percentage):
        self.p_Root = percentage
    def inValidate(self):
        self.isValid = False
        if self.father:
            self.father.inValidate()
    def getHash(self):
        if self.isValid:
            return self.hashcode
        digester = hashlib.md5()
        digester.update(self.methodName)
        for child in self.children:
            digester.update(child.getHash())
        self.hashcode = digester.hexdigest()
        self.isValid = True
        return self.hashcode
    def merge(self, node):
        self.cnt = self.cnt + node.cnt
        self.executeTime = self.executeTime + node.executeTime
        if int(self.maxTime) < int(node.maxTime):
            self.maxTime = node.maxTime
        if self.minTime > node.minTime:
            self.minTime = node.minTime
        for index, child in enumerate(self.children):
            child.merge(node.children[index])
    def mergeDifferent(self, node):
        self.cnt = self.cnt + node.cnt
        children = self.children
        isFind = False
        self.executeTime = self.executeTime + node.executeTime
        if self.maxTime < node.maxTime:
            self.maxTime = node.maxTime
        if self.minTime > node.minTime:
            self.minTime = node.minTime
        for child in node.children:
            for _child in self.children:
                if _child.methodName == child.methodName:
                    if _child.maxTime < child.maxTime:
                        _child.maxTime = child.maxTime
                    if _child.minTime > child.minTime:
                        _child.minTime = child.minTime
                    _child.mergeDifferent(child)
                    isFind = True
                    break
            if isFind is  False:
                # not find
                self.children.append(child)
                child.father = self
            isFind = False
    def calcuAvg(self, total):
        child_total = 0
        for child in self.children:
            child_total = child_total + child.executeTime
        self.percentageRoot = 1.0 * (self.executeTime  - child_total ) / total
        self.avgTime = 1.0 * (self.executeTime - child_total) / self.cnt
        try:
            self.percentageFather = 1.0 * self.executeTime / (self.father.executeTime)
        except:
            pass
        for child in self.children:
            child.calcuAvg(total)
    def calcuPercentage(self, total):
        self.percentageRoot = 1.0 * self.executeTime  / total
        for child in self.children:
            child.calcuPercentage(total)
    def __repr__(self):
        str = '  ' * self.depth + "<%s-%s-%s-[root:%s]-[father:%s]-[max:%s]-[min:%s]-[avg:%s]-[score:%s]>\n" % (self.position, self.methodName, self.executeTime, self.percentageRoot, self.percentageFather, self.maxTime, self.minTime, self.avgTime, self.score)
        for child in self.children:
           # str = str + '  ' * child.depth + "<%s-%s-%d-[%s]-[%s]>\n" % (child.position, child.methodName, child.executeTime, child.percentageRoot, child.percentageFather)
            str = str + child.__repr__()
        return str
    def traverse(self, methodLst = None):
        getJsonAndScore = False
        if methodLst is not None:
            getJsonAndScore = True
        jsonVal = {}
        if getJsonAndScore:
            for method in methodLst:
                if self.methodName == method[0]:
                    self.score = method[1]['score']
                    break
            jsonVal['name'] = self.methodName
            jsonVal['score'] = self.score
            if len(self.children) > 0:
                jsonVal['children'] = []
        nodes = []

        for child in self.children:
            if getJsonAndScore:
                jsonVal['children'].append(child.traverse(methodLst))
            else:
                nodes.append(child)
                nodes = nodes + child.traverse()
        if getJsonAndScore:
            return jsonVal
        else:
            return nodes
    def check_validation(self):
        child_total = 0
        for child in self.children:
            child_total = child_total + child.executeTime
        if child_total > self.executeTime:
            return False
        else:
            return True
class Tree(object):
    def __init__(self, serviceId, totalTime):
        self.serviceId = serviceId
        self.executeTime = totalTime
        self.root = Node({'name':'root','execute_time': totalTime, 'position':'-1'})
        self.hot_spot = None
    def insert(self, node):
        self.findFather(node)
    def findFather(self, node):
        node_position = node.position.split('.')
        tree = self.root.children
        father = self.root
        for depth, p in enumerate(node_position):
            if len(tree) < int(p):
                node.depth = depth + 1
                node.father = father
                # recalcu the hashcode
                father.inValidate()
                tree.append(node)
            else:
                father = tree[int(p)-1]
                tree = tree[int(p)-1].children
        return father
    def merge(self, tree):
        # for totally same tree
        if self.root.hashcode == tree.root.hashcode:
            self.root.merge(tree.root)
            return True
        else:
            return False
    def mergeDifferent(self, tree):
        self.root.mergeDifferent(tree.root)
    def calcuTreePercentage(self):
        self.root.calcuPercentage(self.root.executeTime)
    def calcuTreeAvg(self):
        self.root.calcuAvg(self.root.executeTime)
    def check_validation(self):
        nodes = self.traverse()
        for n in nodes:
            if n.check_validation() is False:
                #logger.info("initialize data ERROR: " + n.methodName)
                pass
    def checkIsValid(self):
        sum = 0
        nodes = self.traverse()
        for node in nodes:
            sum  = sum + node.percentageRoot
        logger.debug("tree sum: " + str(sum))
    def traverse(self):
        return self.root.traverse()
    def addScoreTagAndToJson(self, methodLst, sessionid):
        logger.info("sessionid: " + sessionid)
        directory = os.path.join(settings.JSON_ROOT, sessionid)
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = os.path.join(directory, str(self.serviceId)) + '.json'
        try:
            f = open(filename, 'w+')
            json.dump(self.root.traverse(methodLst), f, indent = 2)
        except Exception,e:
            logger.error(e)
        finally:
            f.close()
    def get_hotspot(self):
        ret = []
        try:
            if self.hot_spot is not None:
                return self.hot_spot
            nodes = self.root.traverse()
            hot_spot = sorted(nodes, lambda x,y : cmp(x.percentageRoot, y.percentageRoot), reverse = True)
            for spot in hot_spot:
                if spot.percentageRoot > 0.1 :
                    ret.append({'method_name' : spot.methodName, 'percentage': spot.percentageRoot})
            self.hot_spot = ret
        except Exception, e:
            print e
        return ret
    def __repr__(self):
        return str(self.serviceId) + '\n' + self.root.__repr__()


class InvertedIndex:
    def __init__(self):
        self.__table = {}
    def __len__(self):
        return len(self.__table.items())
    def __contains__(self, methodNode):
        return methodNode.methodName in self.__table.keys()
    def insert(self, methodNode, service):
        if methodNode in self:
            services = self.__table[methodNode.methodName]['services']
            if service in services.keys():
                services[service] = services[service] + methodNode.percentageRoot
            else:
                services[service] = methodNode.percentageRoot
            if self.__table[methodNode.methodName]['max'] < methodNode.maxTime :
                self.__table[methodNode.methodName]['max'] = float("%0.2f" % methodNode.maxTime)
            if self.__table[methodNode.methodName]['min'] > methodNode.minTime:
                self.__table[methodNode.methodName]['min'] = float("%0.2f" % methodNode.minTime)
            avg = ( self.__table[methodNode.methodName]['avg'] * self.__table[methodNode.methodName]['cnt'] + methodNode.executeTime) * 1.0  / (self.__table[methodNode.methodName]['cnt'] + methodNode.cnt)
            self.__table[methodNode.methodName]['avg'] = float("%0.2f" % avg)
            self.__table[methodNode.methodName]['cnt'] = self.__table[methodNode.methodName]['cnt'] + methodNode.cnt
        else:
            services = {service : methodNode.percentageRoot}
            self.__table[methodNode.methodName] = {}
            self.__table[methodNode.methodName]['services'] = services
            self.__table[methodNode.methodName]['max'] =  float("%0.2f" % methodNode.maxTime)
            self.__table[methodNode.methodName]['min'] =  float("%0.2f" % methodNode.minTime)
            self.__table[methodNode.methodName]['avg'] =  float("%0.2f" % methodNode.avgTime)
            self.__table[methodNode.methodName]['cnt'] =  methodNode.cnt

    def __getitem__(self, attribute):
        return self.__table[attribute]
    def calcuScore(self):
        for method, methodinfo in self.__table.items():
            sum = 0
            avg = 0
            services = methodinfo['services']
            for i,j in services.items():
                sum = sum + j ** 2
                avg = avg + j
            R = math.sqrt(sum * 1.0 / len(services.keys()))
            avg = avg * 1.0 / len(services.keys())
            stdSum = 0
            for i,j in services.items():
                stdSum = stdSum + (j - avg) ** 2
            std = math.sqrt(stdSum * 1.0 / len(services.keys()))
            score = R - std
            self[method]['score'] = float('%0.3f' % score)
        self.rank()
    def rank(self):
        # must call after calcuScore has been called
        self.rankLst = sorted(self.__table.items(), lambda x,y : cmp(x[1]['score'], y[1]['score']), reverse = True)
    def __repr__(self):
        str = ''
        for key,val in self.__table.items():
            str = str +  "===============method name : %s =====================\n" % key
            str = str +  "[max:%s][min:%s][avg:%s][cnt:%s]\n" % (val['max'], val['min'], val['avg'], val['cnt'])
            services = val['services']
            for i,j in services.items():
                str = str +  "<%s-%s>\n" % (i, j)
        return str
