import os
import re
import time
import copy
import signal
import logging

import requests


API_URL = 'https://api.telegram.org/'

class TgMessage:
    def __init__(self, **kwargs):
        self.type = kwargs.pop('type') if kwargs.get('type') else 'telegram'
        self.token = kwargs.pop('token') if kwargs.get('token') else None
        self.offset = kwargs.pop('offset') if kwargs.get('offset') else 0
        self.command = kwargs.pop('command') if kwargs.get('command') else None

        super(TgMessage, self).__init__(**kwargs)

    def receiver(self):
        global exit_flag
        exit_flag = False
        def handle(signum, frame):
            global exit_flag
            if not exit_flag:
                exit_flag = True
                logging.getLogger('TgMessageReceiver').warning(f'Hendler kill process: PID {os.getpid()}')

        signal.signal(signal.SIGINT, handle)
        signal.signal(signal.SIGTERM, handle)

        logging.getLogger('TgMessageReceiver')\
            .info(f'Token (PID {os.getpid()}): {re.search("^[0-9]+", self.token).group()}')
        payload = {}
        messages = []

        while not exit_flag:
            if self.offset:
                payload = {'offset': int(self.offset + 1)}

            https_proxy = self._redis.hget(f'{self._redis_prefix}settings:proxy', 'https').decode('UTF-8')

            self.offset, messages = getUpdates(self.token, self.offset, https_proxy=https_proxy,
                                               cls=type(self))

            for message in messages:
                logging.getLogger('TelegramReceiver').debug(f'Receive message: {message}')
                self._redis.lpush(f'{self._redis_prefix}{self.token}:messages:in', message.dump())

            time.sleep(self._sleep)

    def transmitter(self):
        global exit_flag
        exit_flag = False
        def handle(signum, frame):
            global exit_flag
            if not exit_flag:
                exit_flag = True
                logging.getLogger('TgMessageTransmitter').warning(f'Hendler kill process: PID {os.getpid()}')

        signal.signal(signal.SIGINT, handle)
        signal.signal(signal.SIGTERM, handle)

        logging.getLogger('TgMessageTransmitter').info(f'Token (PID {os.getpid()}): {re.search("^[0-9]+", self.token).group()}')

        url = f'{API_URL}bot{self.token}/sendMessage'

        while not exit_flag:
            msg = self.get_out()

            if msg:
                logging.getLogger('TgMessageTransmitter').debug(f'Transmitte message: {msg}')

                payload = {'chat_id': msg.replay_to_id, 'text': msg.text}

                https_proxy = self._redis.hget(f'{self._redis_prefix}settings:proxy', 'https').decode('UTF-8')

                if https_proxy:
                    proxy = {'https': https_proxy}
                else:
                    proxy = {}

                try:
                    r = requests.post(url, json=payload, proxies=proxy)
                    data = r.json()
                    logging.getLogger('TgMessageTransmitter').debug(f'Server return: {data.get("ok", False)}')
                except:
                    logging.getLogger('TgMessageTransmitter').error('Connection error')

            time.sleep(self._sleep)

    def get(self):
        msg = self._redis.rpop(f'{self._redis_prefix}{self.token}:messages:in')
        if msg:
            return type(self).load(msg)
        else:
            return None

    def get_out(self):
        msg = self._redis.rpop(f'{self._redis_prefix}{self.token}:messages:out')
        if msg:
            return type(self).load(msg)
        else:
            return None

    def send(self):
        logging.getLogger('send_message').debug(f'Send_message, {self} ({self._redis_prefix}{self.token}:messages:out)')
        if self._redis.lpush(f'{self._redis_prefix}{self.token}:messages:out', self.dump()):
            return True
        else:
            return False

def parse(data, token, cls=TgMessage):
    offset = 0
    messages = []
    if data.get('ok', False):
        for result in data['result']:
            if result['update_id'] > offset:
                offset = result['update_id']
            message = result.get('message', None)
            if message:
                tg_message = cls()
                tg_message.text = message.get('text', None)
                tg_message.type = 'telegram'
                tg_message.token = token
                tg_message.from_id = message['from'].get('id', None)
                tg_message.from_name =\
                    f"{message['from'].get('first_name', '')} {message['from'].get('last_name', '')}"
                tg_message.replay_to_id = message['chat'].get('id', None)
                tg_message.replay_to_name =\
                    f"{message['chat'].get('first_name', '')} {message['chat'].get('last_name', '')}"
                entities = result['message'].get('entities', [])
                for entitie in entities:
                    if entitie.get('type', None) == 'bot_command':
                        tg_message.command =\
                            message['text'][entitie['offset']:entitie['offset'] + entitie['length']]
                messages.append(tg_message)
    return offset, messages

def getUpdates(token, offset=0, https_proxy=None, cls=TgMessage):
    url = f'{API_URL}bot{token}/getUpdates'
    print(url)

    payload = {}
    messages = []

    if offset:
        payload = {'offset': int(offset + 1)}

    if https_proxy:
        proxy = {'https': https_proxy}
    else:
        proxy = {}

    try:
        r = requests.post(url, json=payload, proxies=proxy)
        data = r.json()
        offset, messages = parse(data, token, cls)
    except:
        logging.getLogger('TelegramReceiver').error('Connection error')

    return offset, messages
