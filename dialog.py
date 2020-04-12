import logging

from dialog_machine.main import DialogMachine

from settings import Settings


def new_message(msg, text=''):
    settings = Settings()
    new_msg = type(msg)(
        text=text,
        replay_to_id=msg.replay_to_id,
        type=msg.type,
        token=msg.token,
        redis=settings.redis_connect,
        sleep=settings.sleep
    )
    return new_msg

class Dialog(DialogMachine):
    DIALOG = ['hello', 'nice']

    def hello(self, msg):
        logging.getLogger('DialogMachine').info(f'Dialog hello: {msg}')
        new_msg = new_message(msg, text=f'Привет, {msg.from_name}')
        self.next_hop += 1
        return new_msg.send()

    def nice(self, msg):
        logging.getLogger('DialogMachine').info(f'Dialog nice: {msg}')
        new_msg = new_message(msg, text='Здорово!')
        self.next_hop += 1
        return new_msg.send()
