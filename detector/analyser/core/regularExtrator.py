import logging
import re
from config import CoreConfigure
# logger configure
logging.basicConfig(level = logging.DEBUG,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("regularExtractor")

class regularExtrator(object):
    '''
        <field name> - <offset> - <description>
        log_level | 0 | log_level
        date | 1 | log date
        time | 2 | log time
        loggername | 3 | loggername
        thread_id | 4 | thread id
        caller_id | 5 | called id
        certificated_id | 6 | certificated_id
        request_id | 7 | request_id
        thread_name | 8 | thread_name
        record_sequence_id | 9 | record_sequence_id
        position | 10 | the position of method in whole call tree
        method_name | 11 | method name
        service_flag | 12 | {serviceid, entity_name, criteria}
        criteria | 15 | criteria
    '''
    def __init__(self):
        pass
    def extra(self, line):
        try:
            # TODO
            # put the regular pattern to configure file
            pattern = re.compile(r'(?P<log_level>[A-Z]+)>(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}:\d{2}),\d{3} (?P<logname>[a-zA-Z]+)\[Thread-(?P<ThreadID>\d+)\]-\[ClientRequestID:\]-\[CallerID:(?P<CallerID>[A-Z0-9]+)\]-\[CertificateID:(?P<CertificateID>[0-9a-z\-]*)\]-\[Request ID:(?P<RequestID>[0-9a-z\-]*)\]: \[Thread Name:(?P<Threadname>.*)\]\t\[Record Sequence ID: +(?P<SequenceID>\d+)\]\t\[Work Name: *(?P<position>[0-9\.]*) *Call (?P<methodname>[a-zA-Z\.\- =\(\):0-9,]*)(?P<serviceID>--.*NUMBER\(\d*\).*)*\]\tTakes\(nano Sec\):(?P<executeTime>\d+)')
            ret_val = re.match(pattern, line).groups()
            # check contain Service ID
            ret_lst = []
            for i in range(12):
                ret_lst.append(ret_val[i])

            if ret_val[12] is not None:
                ret = re.match(r'.*NUMBER\((?P<serviceID>\d+)\) ENTITY_NAME\((?P<entityname>.*)\) CRITERIA:\[(?P<criteria>.*?)\]', ret_val[12]).groups()
                serviceId = {'serviceid': ret[0], 'entity_name' : ret[1], 'criteria' : ret[2]}
                ret_lst.append(serviceId)
            else:
                ret_lst.append(None)
            # executeTime
            ret_lst.append(ret_val[13])
            return ret_lst
        except Exception, e:
            logger.error(e)
            return None


if __name__ == "__main__":
    pass
