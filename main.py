import os
import re
import time
import logging
import signal
from multiprocessing import Process

from settings import Settings
from message import Message
from dialog import Dialog


if __name__ == '__main__':
    settings = Settings()

    if settings.debug:
        logging.basicConfig(
            level='DEBUG',
            format='%(process)d %(levelname)s %(name)s %(lineno)s %(message)s'
        )
    else:
        logging.basicConfig(
            level='INFO',
            filename='logs/bot.log',
            format='%(asctime)s %(process)d %(levelname)s %(name)s %(lineno)s %(message)s'
        )

    logging.info(f'Starting (PID {os.getpid()})')

    if not settings.redis_connect.llen('tg:settings:tokens'):
        for token in settings.telegram['tokens']:
            settings.redis_connect.lpush('tg:settings:tokens', token)

    if settings.proxy.get('HTTPS', None):
        settings.redis_connect.hset('tg:settings:proxy', 'https', settings.proxy['HTTPS'])

    def dialog(transport, token):
        global exit_flag
        exit_flag = False
        def handle(signum, frame):
            global exit_flag
            if not exit_flag:
                exit_flag = True
                logging.getLogger('dialog').warning(f'Hendler kill process: PID {os.getpid()}')

        signal.signal(signal.SIGINT, handle)
        signal.signal(signal.SIGTERM, handle)

        logging.getLogger('dialog').info(f'Token (PID {os.getpid()}): {re.search("^[0-9]+", token).group()}')

        dialogs = {}

        while not exit_flag:
            msg = transport.get()
            if msg:
                cur_dialog = dialogs.get(msg.replay_to_id, Dialog())
                cur_dialog.response(msg)
                dialogs[msg.replay_to_id] = cur_dialog
                #try:
                #    dialogs[msg.replay_to_id].response(msg)
                #except KeyError:
                #    dialogs[msg.replay_to_id] = Dialog()
                #    dialogs[msg.replay_to_id].response(msg)
            time.sleep(transport._sleep)

    procs = []

    for i in range(0, settings.redis_connect.llen('tg:settings:tokens')):
        token = settings.redis_connect.lindex('tg:settings:tokens', i).decode('UTF-8')

        message = Message(
            type='telegram',
            token=token,
            redis=settings.redis_connect,
            sleep=settings.sleep
        )

        proc = Process(target=message.receiver, name=f'TelegramReceiver: {re.search("^[0-9]+", token).group()}')
        procs.append(proc)

        proc = Process(target=message.transmitter, name=f'TelegramTransmitter: {re.search("^[0-9]+", token).group()}')
        procs.append(proc)

        proc = Process(target=dialog, args=(message,token), name=f'dialog: {re.search("^[0-9]+", token).group()}')
        procs.append(proc)

    for proc in procs:
        proc.start()



# Exit procedures

    def exit_handle(signum, frame):
        for proc in procs:
            proc.terminate()

        for proc in procs:
            proc.join()

        logging.warning(f'Terminate process: PID {proc.pid}')

    signal.signal(signal.SIGINT, exit_handle)
    signal.signal(signal.SIGTERM, exit_handle)

    for proc in procs:
        proc.join()

    logging.warning(f'Exit (PID {os.getpid()})')
