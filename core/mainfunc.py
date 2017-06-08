"""Standard __main__ handler that covers most cases"""
from __future__ import print_function, with_statement

import errno
import logging
import logging.config
import os
import os.path
import sys

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'console': {
            'format': '[%(asctime)s][%(levelname)s] %(name)s '
                      '%(pathname)s:%(funcName)s:%(lineno)d | %(message)s',
        },
    },

    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
        #        'sentry': {
        #            'level': 'ERROR',
        #            'class': 'raven.handlers.logging.SentryHandler',
        #            'dsn': '',
        #            },
    },

    'loggers': {
        '': {
            #            'handlers': ['console', 'sentry'],
            'handlers': ['console', ],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}


def usage(binname):
    """Prints the default usage instructions"""
    print("""
    Usage:
      {} [config_file]
    """.format(binname))


def main(binname, controller_klass, autorun=True, override_usage=None, eventloop=None):
    """Boilerplate main-function"""
    logging.config.dictConfig(LOGGING)

    if not eventloop:
        import zmq.eventloop
        from tornado.ioloop import IOLoop

        zmq.eventloop.ioloop.install()
        eventloop = IOLoop.instance()

    if len(sys.argv) > 1 and sys.argv[1] == 'help':
        if override_usage:
            override_usage(binname)
        else:
            usage(binname)
        sys.exit(0)

    if len(sys.argv) < 2:
        config_file = binname.replace('.py', '_config.json')
    else:
        config_file = sys.argv[1]

    if not os.path.exists(config_file):
        if override_usage:
            override_usage(binname)
        else:
            usage(binname)
        print("File {} does not exist".format(config_file))
        sys.exit(errno.ENOENT)

    pgm_name = os.path.basename(binname).replace('.py', '')
    instance = controller_klass(
        mainloop=eventloop,
        config_root_name=pgm_name,
        config_file=config_file,
        logger_name=pgm_name,
    )
    instance.hook_signals()
    if autorun:
        try:
            instance.run()
        except KeyboardInterrupt:
            instance.quit()
    return instance
