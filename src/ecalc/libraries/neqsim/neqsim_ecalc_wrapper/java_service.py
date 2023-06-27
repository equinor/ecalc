import os
from os import path

from py4j.java_gateway import JavaGateway

gateway = None
local_os_name = os.name
colon = ":"
if local_os_name == "nt":
    colon = ";"


def create_classpath(jars):
    """Create path to NeqSim .jar file"""
    resources_dir = path.dirname(__file__) + "/lib"
    return colon.join([path.join(resources_dir, jar) for jar in jars])


def start_server():
    """Start JVM for NeqSim Wrapper"""
    global gateway
    jars = ["NeqSim.jar"]
    classpath = create_classpath(jars)
    import logging

    # This logger (named "py4j") is needed to enable logging from java https://www.py4j.org/faq.html#how-to-turn-logging-on-off
    logging.getLogger("py4j").setLevel(logging.ERROR)
    return JavaGateway.launch_gateway(classpath=classpath, die_on_exit=True)
