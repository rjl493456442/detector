import hashlib
import math
import json
from config import CoreConfigure, logging
import os
from django.conf import settings
import datetime

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
        self.percentageChildren = 0
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
        self.percentageChildren = 1.0 * child_total / self.executeTime
        self.avgTime = 1.0 * (self.executeTime - child_total) / self.cnt
        try:
            self.percentageFather = 1.0 * self.executeTime / (self.father.executeTime)
        except:
            pass
        for child in self.children:
            child.calcuAvg(total)
    def calcuPercentage(self, total):
        """ calcu percentage
        Args:
            1) total: service total execution time. and that is root node execution time
        """
        self.percentageRoot = 1.0 * self.executeTime  / total
        child_exection_total = 0
        for child in self.children:
            child.calcuPercentage(total)
            child_exection_total += child.executeTime
    def __repr__(self):
        str = '  ' * self.depth + "<%s-%s-%s-[root:%s]-[father:%s]-[max:%s]-[min:%s]-[avg:%s]-[score:%s]>\n" % (self.position, self.methodName, self.executeTime, self.percentageRoot, self.percentageFather, self.maxTime, self.minTime, self.avgTime, self.score)
        for child in self.children:
           # str = str + '  ' * child.depth + "<%s-%s-%d-[%s]-[%s]>\n" % (child.position, child.methodName, child.executeTime, child.percentageRoot, child.percentageFather)
            str = str + child.__repr__()
        return str
    def traverse(self, methodLst = None):
        """ traverse the entire tree from the root node
        Args:
            1) methodLst: ranked method list contain mapping between function and web service
        Returns:
            1) if methodLst not exists, return all node of the tree
            2) if methodLst exists, return all node information contains name, score, avg execution time, percentage
        Raises:
        """
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
            jsonVal['avg'] = round(self.avgTime, 2)
            jsonVal['percentage'] = round(self.percentageRoot * 100, 2)
            jsonVal['percentageChildren'] = round(self.percentageChildren * 100, 2)
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
    def __init__(self, serviceId, totalTime, occurtime):
        self.serviceId = serviceId
        self.executeTime = totalTime
        self.root = Node({'name':'root','execute_time': totalTime, 'position':'-1'})
        self.hot_spot = None
        self.occurtime =[occurtime]
        self.response_time = [{
            'occur_time': occurtime.strftime("%H:%M:%S"),
            'response_time': totalTime
        }]
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
        self.response_time.extend(tree.response_time)
        self.occurtime.extend(tree.occurtime)
        if self.root.hashcode == tree.root.hashcode:
            self.root.merge(tree.root)
            return True
        else:
            return False
    def mergeDifferent(self, tree):
        self.occurtime.extend(tree.occurtime)
        self.response_time.extend(tree.response_time)
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
    def addScoreTagAndToJson(self, methodLst, username, datetime):
        """ 1)calcu score for each node belong to tree
            2)save in json format
        Args:
            1)methodLst: list contains mapping between function and web service which from inverted index
            2)username: use to specify the user directory
            3)datetime: if exists, save to the relavant date directory which belong to the user
                        otherwise, save to temp directory

        Important:
            this function only called by final tree(which means all merge works has done)
        """
        user_directory = os.path.join(settings.JSON_ROOT, username)
        if not os.path.exists(user_directory):
            os.makedirs(user_directory)

        datetime_directory = os.path.join(user_directory, datetime)
        if not os.path.exists(datetime_directory):
            os.makedirs(datetime_directory)

        filename = os.path.join(datetime_directory, str(self.serviceId)) + '.json'
        try:
            f = open(filename, 'w+')
            json.dump(self.root.traverse(methodLst), f, indent = 2)
        except Exception,e:
            logger.error(e)
        finally:
            f.close()
    def get_hotspot(self):
        find_in_ret_list = False
        ret = []
        try:
            if self.hot_spot is not None:
                return self.hot_spot
            nodes = self.root.traverse()
            hot_spot = sorted(nodes, lambda x,y : cmp(x.percentageRoot, y.percentageRoot), reverse = True)
            for spot in hot_spot:
                # reset flag
                find_in_ret_list = False
                if spot.percentageRoot > 0.1 :
                    for _spot in ret:
                        if _spot['method_name'] == spot.methodName:
                            _spot['percentage'] += spot.percentageRoot
                            find_in_ret_list = True
                    # not found in ret list
                    if find_in_ret_list is False:
                        ret.append({'method_name' : spot.methodName, 'percentage': spot.percentageRoot})
            self.hot_spot = ret
        except Exception, e:
            logger.error(e)
        return ret
    def save_occur_time(self, username, datetime_str):
        date_table = DateTimeHashTable()
        for occur_date in self.occurtime:
            date_table.insert(occur_date)
        date_lst = date_table.export()
        date_table.save_to_file(date_lst, username, datetime_str, self.serviceId)
    def save_response_time(self, username, datetime):
        user_directory = os.path.join(settings.JSON_ROOT, username)
        if not os.path.exists(user_directory):
            os.makedirs(user_directory)

        datetime_directory = os.path.join(user_directory, datetime)
        if not os.path.exists(datetime_directory):
            os.makedirs(datetime_directory)

        file_prefix = self.serviceId + "_response"
        filename = os.path.join(datetime_directory, file_prefix) + '.json'
        try:
            f = open(filename, "w+")
            json.dump(self.response_time, f, indent = 2)
        except Exception, e:
            logger.error(e)
        finally:
            f.close()
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
        try:
            if methodNode in self:
                services = self.__table[methodNode.methodName]['services']
                if service in services.keys():
                    # update percentageRoot
                    services[service][0] = services[service][0] + methodNode.percentageRoot
                    # update percentageChildren
                    if services[service][1] is None:
                        services[service][1] = [methodNode.percentageChildren]
                    else:
                        services[service][1].append(methodNode.percentageChildren)
                else:
                    services[service] = [methodNode.percentageRoot, [methodNode.percentageChildren]]
                if self.__table[methodNode.methodName]['max'] < methodNode.maxTime :
                    self.__table[methodNode.methodName]['max'] = float("%0.2f" % methodNode.maxTime)
                if self.__table[methodNode.methodName]['min'] > methodNode.minTime:
                    self.__table[methodNode.methodName]['min'] = float("%0.2f" % methodNode.minTime)
                avg = ( self.__table[methodNode.methodName]['avg'] * self.__table[methodNode.methodName]['cnt'] + methodNode.executeTime) * 1.0  / (self.__table[methodNode.methodName]['cnt'] + methodNode.cnt)
                self.__table[methodNode.methodName]['avg'] = float("%0.2f" % avg)
                self.__table[methodNode.methodName]['cnt'] = self.__table[methodNode.methodName]['cnt'] + methodNode.cnt
            else:
                service_info = [methodNode.percentageRoot, [methodNode.percentageChildren]]
                services = {service : service_info}
                self.__table[methodNode.methodName] = {}
                self.__table[methodNode.methodName]['services'] = services
                self.__table[methodNode.methodName]['max'] =  float("%0.2f" % methodNode.maxTime)
                self.__table[methodNode.methodName]['min'] =  float("%0.2f" % methodNode.minTime)
                self.__table[methodNode.methodName]['avg'] =  float("%0.2f" % methodNode.avgTime)
                self.__table[methodNode.methodName]['cnt'] =  methodNode.cnt
        except Exception,e:
            logger.error(e)

    def __getitem__(self, attribute):
        return self.__table[attribute]
    def calcuScore(self):
        for method, methodinfo in self.__table.items():
            sum = 0
            avg = 0
            services = methodinfo['services']
            for i,j in services.items():
                sum = sum + j[0] ** 2
                avg = avg + j[0]
            R = math.sqrt(sum * 1.0 / len(services.keys()))
            avg = avg * 1.0 / len(services.keys())
            stdSum = 0
            for i,j in services.items():
                stdSum = stdSum + (j[0] - avg) ** 2
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
class DateTimeHashTable(object):
    def __init__(self, flag = None):
        self.__dates = {}
        if flag:
            self.flag = flag
        else:
            # set default format by minute
            self.flag = 0
    def __contain__(self, date):
        return date in self.__dates.keys()
    '''
        use flag to specific precision of date
        flag:
            None -> default Hour
            1    -> Day
            2    -> Month
            3    -> Year
    '''
    def insert(self, date):
        # convert date
        if self.flag == 0:
            date = DateTimeHashTable.convertDateByMinute(date)
        elif self.flag == 1:
            date = DateTimeHashTable.convertDateByHour(date)
        else:
            date = DateTimeHashTable.convertDateByDay(date)
        # insert
        if date in self.__dates:
            self.__dates[date] = self.__dates[date] + 1
        else:
            self.__dates[date] = 1
    @staticmethod
    def convertDateByMinute(date):
        return datetime.datetime(date.year, date.month, date.day, date.hour, date.minute, 0)
    @staticmethod
    def convertDateByHour(date):
        return datetime.datetime(date.year, date.month, date.day, date.hour, 0, 0)
    @staticmethod
    def convertDateByDay(date):
        return datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
    def export(self):
        date_content = []
        for date, occur in self.__dates.items():
            if self.flag == 0:
                date_str = date.strftime("%Y-%m-%d %H:%M")
            elif self.flag == 1:
                date_str = date.strftime("%Y-%m-%d %H")
            else:
                date_str = date.strftime("%Y-%m-%d")
            date_content.append({"year": date_str, "value": occur})
        return date_content
    def save_to_file(self, date_content, username, datetime_str, serviceId = None):
        user_directory = os.path.join(settings.JSON_ROOT, username)
        if not os.path.exists(user_directory):
            os.makedirs(user_directory)

        datetime_directory = os.path.join(user_directory, datetime_str)
        if not os.path.exists(datetime_directory):
            os.makedirs(datetime_directory)

        if serviceId:
            file_prefix = serviceId + "_date"
        else:
            file_prefix = "date"
        filename = os.path.join(datetime_directory, file_prefix) + '.json'
        try:
            f = open(filename, 'w+')
            json.dump(date_content, f, indent = 2)
        except Exception,e:
            logger.error(e)
        finally:
            f.close()

class HistroyRecord:
    '''
        file_list
        services
        rank_list
        total_size
        elapsed
    '''
    def __init__(self):
        self.__info = {}

    def add_info(self, field, value):
        self.__info[field] = value
    def check_validation(self):
        pass

    def save_record(self, username, datetime_str = None):
        if datetime_str is None:
            datetime_str = "temp"
        user_directory = os.path.join(settings.JSON_ROOT, username)
        if not os.path.exists(user_directory):
            os.makedirs(user_directory)

        datetime_directory = os.path.join(user_directory, datetime_str)
        if not os.path.exists(datetime_directory):
            os.makedirs(datetime_directory)
        file_prefix = "record"
        filename = os.path.join(datetime_directory, file_prefix) + '.json'
        try:
            f = open(filename, 'w+')
            json.dump(self.__info, f, indent = 2)
        except Exception, e:
            logger.error(e)
        finally:
            f.close()
    def show_content(self):
        logger.info(self.__info)
def unittest():
    date_table = DateTimeHashTable()
    for i in xrange(60):
        date = datetime.datetime(2016,2,29,23,i,0)
        date_table.insert(date)
    print date_table.export()
if __name__ == "__main__":
    unittest()
