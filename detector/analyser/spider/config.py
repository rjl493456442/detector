import ConfigParser
import logging
import os

basepath = os.path.dirname(os.path.abspath(__file__))


class CoreConfigure(object):
    '''
        initialize a configure reader with default configure file path
        usage:
        obj = CoreConfigure(cfg_file_path)
        dic = obj.get_configure(cfg_section)
    '''
    def __init__(self, config_file = basepath + "/configure/core.cfg"):
        self.configure_instance = ConfigParser.ConfigParser()
        self.configure_instance.read(config_file)
    def get_config_section_map(self, section):
        cfg_dict = {}
        options = self.configure_instance.options(section)
        for option in options:
            try:
                cfg_dict[option] = self.configure_instance.get(section, option)
            except:
                cfg_dict[option] = None
        return cfg_dict

if __name__ == "__main__":
    config = CoreConfigure()
