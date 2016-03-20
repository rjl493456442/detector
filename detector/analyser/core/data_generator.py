'''
    modify log file by script
    author: gary rong
    date: 2016-03-12
'''


import sys
import logging
from random import randint
import re
# logger setting

logging.basicConfig(level = logging.DEBUG,
                    format = '%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                   )
logger = logging.getLogger("data generator")

input_file = ""
output_file = ""
delta = 0.0


class Generator(object):
    def __init__(self, input_file, output_file, delta):
        self.input_file = input_file
        self.output_file = output_file
        self.delta = delta
        # to store whole elapsed time for each method
        self.remain_time_stack = []
        self.method_position_stack = []
        try:
            self.f_input = open(input_file, 'r')
            self.f_output = open(output_file, 'w+')
        except Exception, e:
            logger.error(e)

    def process(self):
        while True:
            line = self.f_input.readline()
            if line:
                if Generator.is_begin_log_entry(line):
                    self.f_output.write(line)
                elif Generator.is_end_log_entry(line):
                    self.method_position_stack = []
                    self.remain_time_stack = []
                    self.f_output.write(line)
                else:
                    # need to modify elapsed time data
                    start_pos = line.find("Takes(nano Sec):") + len("Takes(nano Sec):")
                    end_pos = line.find("\r\n")
                    elapsed_time = int(line[start_pos: end_pos])

                    pattern = re.compile(r'.*Work Name: *([0-9\.]*) *Call')
                    method_position = re.match(pattern, line).group(1)
                    if method_position == '':
                        self.method_position_stack.append(method_position)
                        self.method_position_stack.append(method_position)
                        elapsed_time_new = self.get_new_elapsed_time(elapsed_time)
                        # save to remain stack
                        self.remain_time_stack.append(elapsed_time_new)
                        self.remain_time_stack.append(elapsed_time_new)

                    else:
                        if len(method_position.split('.')) <= len(self.method_position_stack[-1].split('.')):
                            diff = len(self.method_position_stack[-1].split('.')) - len(method_position.split('.')) + 1
                            while diff > 0:
                                self.remain_time_stack.pop()
                                self.method_position_stack.pop()
                                diff -= 1
                        # get remain
                        remain = self.remain_time_stack[-1]
                        elapsed_time_new  = self.get_new_elapsed_time(elapsed_time, remain)
                        self.remain_time_stack[-1] = remain - elapsed_time_new
                        # save remain info
                        self.remain_time_stack.append(elapsed_time_new)
                        self.method_position_stack.append(method_position)
                    # construct output line
                    output_line = line[:start_pos] + "%d\r\n" % elapsed_time_new
                    self.f_output.write(output_line)

            else:
                self.f_input.close()
                self.f_output.close()
                break
    @staticmethod
    def is_begin_log_entry(line):
        if line.find('==Begin==') != -1:
            return True
        return False

    @staticmethod
    def is_end_log_entry(line):
        if line.find('==End==') != -1:
            return True
        return False

    def get_new_elapsed_time(self, elapsed_time, remain = None):
        delta = self.delta
        bottom_limitation = int(elapsed_time * (1 - delta)) + 1
        if remain:
            top_limitation = min(remain, int(elapsed_time * (1 + delta)) - 1)
        else:
            top_limitation = int(elapsed_time * (1 + delta)) -1
        '''
        logger.info("elapsed_time")
        logger.info(elapsed_time)
        logger.info("delta")
        logger.info(delta)
        logger.info("bottom_limitation")
        logger.info(bottom_limitation)
        logger.info("top_limitation")
        logger.info(top_limitation)
        '''
        if top_limitation < 0:
            return 0
        if bottom_limitation > top_limitation:
            bottom_limitation = top_limitation / 2
        new_elapsed_time = randint(bottom_limitation, top_limitation)
        return new_elapsed_time

if __name__ == "__main__":

    num_argv = len(sys.argv)
    if num_argv - 1 != 6:
        logger.error("invalid argv")
        sys.exit()
    index = 1
    while index < len(sys.argv):
        if sys.argv[index].startswith('--'):
            options = sys.argv[index][2:]
            if options == "input_file":
                input_file = sys.argv[index+1]
                index += 2
            elif options == "output_file":
                output_file = sys.argv[index+1]
                index += 2
            elif options == "delta":
                delta = float(sys.argv[index+1])
                index += 2
            else:
                logger.error("invalid argv")
                sys.exit()
    try:
        f = open(input_file, 'r')
        f = open(output_file, 'w')
    except Exception, e:
        logger.error(e)
    # init generator
    generator = Generator(input_file, output_file, delta)
    generator.process()
