import logging
import sys
import re
import time
import act.api


def setup_logging(loglevel="debug", logfile=None, prefix="act"):
    """setup default logging"""

    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {}'.format(loglevel))

    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = "[%(asctime)s] app=" + prefix + " level=%(levelname)s msg=%(message)s"

    if logfile:
        logging.basicConfig(
            level=numeric_level,
            filename=time.strftime(logfile),
            format=formatter,
            datefmt=datefmt)
    else:
        logging.basicConfig(
            level=numeric_level,
            stream=sys.stdout,
            format=formatter,
            datefmt=datefmt)


def snake_to_camel(snake):
    """convert snake_case to camelCase"""

    components = snake.split("_")
    return components[0] + "".join([comp.title() for comp in components[1:]])

# https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
def camel_to_snake(camel):
    """convert camelCase to snake_case"""
    camel = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', camel).lower()


def prepare_params(params, exclude_params=None, ensure_list=None):
    """convert all keys to camelCase and filter out values. As default,
    act_baseurl and user_id is filtered out"""

    if not exclude_params:
        exclude_params = ["act_baseurl", "user_id", "self"]

    # Put entries if list if they not already contained in a list
    if ensure_list:
        for param in ensure_list:
            if param in params and not isinstance(
                    params[param], (list, tuple)):
                params[param] = [params[param]]

    # Filter out params with null Values and convert to camelCase
    return {
        act.api.utils.snake_to_camel(k): v
        for (k, v) in params.items()
        if (v and k not in exclude_params)}
