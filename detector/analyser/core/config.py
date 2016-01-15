import ConfigParser
import logging
import os
basepath = os.path.dirname(os.path.abspath(__file__))

def configSectionMap(configInstance, section):
    cfg_dict = {}
    options = config_instance.options(section)
    for option in options:
        try:
            cfg_dict[option] = config_instance.get(section, option)
        except:
            cfg_dict[option] = None
    return cfg_dict


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
    def get_configure(self, section):
        cfg_dict = {}
        options = self.configure_instance.options(section)
        for option in options:
            try:
                cfg_dict[option] = self.configure_instance.get(section, option)
            except:
                cfg_dict[option] = None
        return cfg_dict


