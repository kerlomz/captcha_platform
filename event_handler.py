#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Author: kerlomz <kerlomz@gmail.com>
import os
import time
from watchdog.events import *
from config import ModelConfig, Config
from graph_session import GraphSession
from interface import InterfaceManager, Interface
from utils import PathUtils


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, conf: Config, model_conf_path: str, interface_manager: InterfaceManager):
        FileSystemEventHandler.__init__(self)
        self.conf = conf
        self.logger = self.conf.logger
        self.name_map = {}
        self.model_conf_path = model_conf_path
        self.interface_manager = interface_manager
        self.init()

    def init(self):
        model_list = os.listdir(self.model_conf_path)
        model_list = [os.path.join(self.model_conf_path, i) for i in model_list if i.endswith("yaml")]
        for model in model_list:
            self._add(model, is_first=True)
        if self.interface_manager.total == 0:
            self.logger.info(
                "\n - Number of interfaces: {}"
                "\n - There is currently no model deployment"
                "\n - Services are not available"
                "\n[ Please check the graph and model path whether the pb file and yaml file are placed. ]".format(
                    self.interface_manager.total,
                ))
        else:
            self.logger.info(
                "\n - Number of interfaces: {}"
                "\n - Current online interface: \n\t - {}"
                "\n - The default Interface is: {}".format(
                    self.interface_manager.total,
                    "\n\t - ".join(["[{}]".format(v) for k, v in self.name_map.items()]),
                    self.interface_manager.default_name
                ))

    def _add(self, src_path, is_first=False, count=0):
        try:
            model_path = str(src_path)
            path_exists = os.path.exists(model_path)
            if not path_exists and count > 0:
                self.logger.error("{} not found, retry attempt is terminated.".format(model_path))
                return
            if 'model_demo.yaml' in model_path:
                self.logger.warning(
                    "\n-------------------------------------------------------------------\n"
                    "- Found that the model_demo.yaml file exists, \n"
                    "- the loading is automatically ignored. \n"
                    "- If it is used for the first time, \n"
                    "- please copy it as a template. \n"
                    "- and do not use the reserved character \"model_demo.yaml\" as the file name."
                    "\n-------------------------------------------------------------------"
                )
                return
            if model_path.endswith("yaml"):
                model_conf = ModelConfig(self.conf, model_path)
                inner_name = model_conf.target_model
                inner_size = model_conf.size_string
                inner_key = PathUtils.get_file_name(model_path)
                for k, v in self.name_map.items():
                    if inner_size in v:
                        self.logger.warning(
                            "\n-------------------------------------------------------------------\n"
                            "- The current model {} is the same size [{}] as the loaded model {}. \n"
                            "- Only one of the smart calls can be called. \n"
                            "- If you want to refer to one of them, \n"
                            "- please use the model key or model type to find it."
                            "\n-------------------------------------------------------------------".format(
                                inner_key, inner_size, k
                            )
                        )
                        break

                inner_value = model_conf.graph_name
                graph_session = GraphSession(model_conf)
                if graph_session.loaded:
                    interface = Interface(graph_session)
                    if inner_name == self.conf.default_model:
                        self.interface_manager.set_default(interface)
                    else:
                        self.interface_manager.add(interface)
                    self.logger.info("{} a new model: {} ({})".format(
                        "Inited" if is_first else "Added", inner_value, inner_key
                    ))
                    self.name_map[inner_key] = inner_value
                    if src_path in self.interface_manager.invalid_group:
                        self.interface_manager.invalid_group.pop(src_path)
                else:
                    self.interface_manager.report(src_path)
                    if count < 12 and not is_first:
                        time.sleep(5)
                        return self._add(src_path, is_first=is_first, count=count+1)

        except Exception as e:
            self.interface_manager.report(src_path)
            self.logger.error(e)

    def delete(self, src_path):
        try:
            model_path = str(src_path)
            if model_path.endswith("yaml"):
                inner_key = PathUtils.get_file_name(model_path)
                graph_name = self.name_map.get(inner_key)
                self.interface_manager.remove_by_name(graph_name)
                self.name_map.pop(inner_key)
                self.logger.info("Unload the model: {} ({})".format(graph_name, inner_key))
        except Exception as e:
            self.logger.error("Config File [{}] does not exist.".format(str(e).replace("'", "")))

    def on_created(self, event):
        if event.is_directory:
            self.logger.info("directory created:{0}".format(event.src_path))
        else:
            model_path = str(event.src_path)
            self._add(model_path)
            self.logger.info(
                "\n - Number of interfaces: {}"
                "\n - Current online interface: \n\t - {}"
                "\n - The default Interface is: {}".format(
                    len(self.interface_manager.group),
                    "\n\t - ".join(["[{}]".format(v) for k, v in self.name_map.items()]),
                    self.interface_manager.default_name
                ))

    def on_deleted(self, event):
        if event.is_directory:
            self.logger.info("directory deleted:{0}".format(event.src_path))
        else:
            model_path = str(event.src_path)
            if model_path in self.interface_manager.invalid_group:
                self.interface_manager.invalid_group.pop(model_path)
            inner_key = PathUtils.get_file_name(model_path)
            if inner_key in self.name_map:
                self.delete(model_path)
            self.logger.info(
                "\n - Number of interfaces: {}"
                "\n - Current online interface: \n\t - {}"
                "\n - The default Interface is: {}".format(
                    len(self.interface_manager.group),
                    "\n\t - ".join(["[{}]".format(v) for k, v in self.name_map.items()]),
                    self.interface_manager.default_name
                ))


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
