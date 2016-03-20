import ConfigParser
import time
from config import  CoreConfigure
from regularExtrator import regularExtrator
from django.conf import settings
import os
import logging
import json
import datetime
logging.basicConfig(level = logging.DEBUG,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("reader")
class Reader(object):
    STATE_UNBEGIN = -1
    STATE_BEGIN = 0
    STATE_GENERAL = 1
    def __init__(self):
        ## origintreeaccray: build call tree from log file, discard the builded tree
        ##                   which children execution time sum less than
        ##                   root node total exetime * origintreeaccray
        self.test_data = []
        self.config = CoreConfigure()
        # default basepath
        self.accuracy = self.config.get_configure('accuracy')['origintreeaccracy']
        # read test data filename
        self.extrator = regularExtrator()
        self.count = 0
        self.finished = False
        self.filter_datetime_begin = None
        self.filter_datetime_end = None
    def execute(self, datetime_begin = None, datetime_end = None, test_data = None):
        """
            method execute is a generator
        """
        # initialize filter data
        self.filter_datetime_begin = datetime_begin
        self.filter_datetime_end = datetime_end
        # initiailize test data
        if test_data is None:
            # for debug mode
            self.test_data = self.get_initial_data()
        else:
            # for release mode
            self.test_data = [os.path.join(settings.MEDIA_ROOT, d) for d in test_data]
        # current state
        self.current_state = Reader.STATE_UNBEGIN

        # initial variable
        # req_info: whole request infomation contain serviceId, called methods
        #           task execute time and etc
        # method_lst : contain all methods in a request

        self.req_info = {}
        self.method_lst = []

        # automatic machine for parser log file to extract request infomation
        for log_file in self.test_data:
            try:
                f = open(log_file, 'r')
                while True:
                    line  = f.readline()
                    if line:
                        # see detail description in regularExtrator file
                        ret_val = self.extrator.extra(line)
                        parse_res = self.state_machine_change(self.current_state, ret_val)
                        if self.finished is True:
                            yield self.req_info
                            self.count = self.count + 1
                            self.clear_up()
                    else:
                        # whole file is processed already
                        f.close()
                        break
            except Exception ,e:
                # handle exception file not exist
                logger.error(e)
    def state_machine_change(self, current_state, reqinfo, *args, **kwargs):
        return {
            -1: self.parse_begin,
            0: self.parse_root,
            1: self.parse_call_method
        }.get(current_state)(reqinfo, *args, **kwargs)
    def parse_begin(self, reqinfo, *args, **kwargs):
        flag_str = "==Begin=="
        try:
            # build datetime of request
            request_datetime = reqinfo[1] + " " + reqinfo[2]
            # convert to datetime object
            datetime_object = datetime.datetime.strptime(request_datetime, "%Y-%m-%d %H:%M:%S")
            # check validation of request datetime
            if self.check_datetime_validation(datetime_object) is False:
                return None
            # set datetime of request
            self.req_info['datetime'] = datetime_object
            # get method name
            line = reqinfo[11]
            if line.find(flag_str) != -1:
                self.current_state = Reader.STATE_BEGIN
        except Exception,e:
            logger.error(e)
        finally:
            return None
    def parse_root(self, reqinfo, *args, **kwargs):
        try:
            #get total time
            total_time = int(reqinfo[13])
            self.req_info['total_time'] = total_time * 1.0 / 1000 / 1000
            self.current_state = Reader.STATE_GENERAL
        except:
            pass
        finally:
            return None
    def parse_call_method(self, reqinfo, *args, **kwargs):
        begin_flag = '==Begin=='
        end_flag = "==End=="
        try:
            # get method info check whether is end
            method_name = reqinfo[11]
            if method_name.find(end_flag) != -1:
                self.parse_finish()
            elif method_name.find(begin_flag) != -1:
                # continuous begin flag, discard previous infomation gathered
                self.current_state = STATE_BEGIN
                self.req_info = {}
                self.method_lst = []
            else:
                method_dic = {}
                if reqinfo[12] is not None:
                    criteria = reqinfo[12]['criteria'].replace(' ','').replace('/','_')
                    criteria_idx = self.strip_criteria_name(criteria)
                    if criteria_idx != -1:
                        self.req_info['serviceId'] = reqinfo[12]['entity_name']+'['  + criteria[0:criteria_idx] + ']'
                    else:
                        self.req_info['serviceId'] = reqinfo[12]['entity_name']+'['  +  criteria + ']'
                idx =  self.strip_method_name(reqinfo[11])
                if idx != -1:
                    method_dic['name'] = reqinfo[11][0:idx]
                else:
                    method_dic['name'] = reqinfo[11]
                exetime = int(reqinfo[13])
                # change to micro second
                method_dic['execute_time'] = exetime * 1.0 / 1000 / 1000
                method_dic['position'] = reqinfo[10]
                self.method_lst.append(method_dic)
        except Exception, e:
            logger.error(e)
        finally:
            return None
    def parse_finish(self):
        self.current_state = Reader.STATE_UNBEGIN
        self.req_info['method_lst'] = self.method_lst
        # DEBUG
        if  self.check_validation():
            self.finished = True
            return self.req_info
        else:
            self.clear_up()
            return None
    def check_validation(self):
        # point one : whether have service ID
        # point two : all children of root node whole execute_time
        #             not less than node execute_time * accuracy
        if 'serviceId' in self.req_info:
            total = self.req_info['total_time']
            sum = 0
            for m in self.req_info['method_lst']:
                if len(m['position'].split('.')) == 1:
                    sum = sum + m['execute_time']
            if sum * 1.0 / total >= float(self.accuracy):
                return True
            else:
                return False
        else:
            return False
    def check_datetime_validation(self, datetime):
        validation = True
        if self.filter_datetime_begin is not None and datetime < self.filter_datetime_begin:
            validation = False
        if self.filter_datetime_end is not None and datetime >  self.filter_datetime_end:
            validation = False
        return validation

    def strip_method_name(self, method_name):
        idx = method_name.find(", output row")
        return idx
    def strip_criteria_name(self, criteria):
        idx = criteria.find("ANDDATE=")
        if idx == -1:
            idx = criteria.find("ANDPUB_KY")
        return idx
    def clear_up(self):
        self.req_info = {}
        self.method_lst = []
        self.finished = False
    def get_initial_data(self):
        basepath = os.path.dirname(os.path.abspath(__file__)) + "/test_data"
        test_data = []
        for key,val in self.config.get_configure("data").items():
            test_data.append(basepath + "/" + val)
        return test_data
def unit_test():
    """
        execute about 70mb size file with in 6 seconds
    """
    test_datetime_begin = datetime.datetime(2014,8,17,17,30,0)
    test_datetime_end = datetime.datetime(2014,8,17,17,32,0)
    start = time.clock()
    reader_obj = Reader()
    # TODO Test
    for itm in reader_obj.execute(datetime_begin = test_datetime_begin, datetime_end = test_datetime_end):
        print itm
    elapsed = (time.clock() - start)
    logger.info("elapsed time:" + str(elapsed))
if __name__ == "__main__":
    unit_test()
