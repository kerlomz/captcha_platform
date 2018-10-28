#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
from watchdog.events import *
from config import ModelConfig, Config
from graph_session import GraphSession
from interface import InterfaceManager, Interface


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, conf: Config, model_conf_path: str, interface_manager: InterfaceManager):
        FileSystemEventHandler.__init__(self)
        self.conf = conf
        self.model_conf_path = model_conf_path
        self.interface_manager = interface_manager
        self.init()

    def init(self):
        model_list = os.listdir(self.model_conf_path)
        for model in model_list:
            if 'model_demo' in model:
                continue
            model_conf = ModelConfig(self.conf, "{}/{}".format(self.model_conf_path, model))
            graph_session = GraphSession(model_conf)
            interface = Interface(graph_session)
            if graph_session.model_name == self.conf.default_model:
                self.interface_manager.set_default(interface)
            else:
                self.interface_manager.add(interface)

    def on_moved(self, event):
        if event.is_directory:
            print("directory moved from {0} to {1}".format(event.src_path, event.dest_path))
        else:
            print("file moved from {0} to {1}".format(event.src_path, event.dest_path))

    def on_created(self, event):
        if event.is_directory:
            print("directory created:{0}".format(event.src_path))
        else:
            print("file created:{0}".format(event.src_path))

    def on_deleted(self, event):
        if event.is_directory:
            print("directory deleted:{0}".format(event.src_path))
        else:

            print("file deleted:{0}".format(event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            print("directory modified:{0}".format(event.src_path))
        else:
            print("file modified:{0}".format(event.src_path))


if __name__ == "__main__":
    pass
    # import time
    # from watchdog.observers import Observer
    # observer = Observer()
    # interface_manager = InterfaceManager()
    # event_handler = FileEventHandler("", interface_manager)
    # observer.schedule(event_handler, event_handler.model_conf_path, True)
    # observer.start()
    # try:
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     observer.stop()
    # observer.join()
