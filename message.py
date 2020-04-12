import json

from telegram import TgMessage


class Message(TgMessage):
    def __init__(self, **kwargs):
        self._sleep = kwargs.pop('sleep') if kwargs.get('sleep') else .5
        self._redis = kwargs.pop('redis') if kwargs.get('redis') else None
        self._redis_prefix = kwargs.pop('redis_prefix') if kwargs.get('redis_prefix') else 'tg:'

        self.text = kwargs.pop('text') if kwargs.get('text') else None
        self.from_id = kwargs.pop('from_id') if kwargs.get('from_id') else None
        self.from_name = kwargs.pop('from_name') if kwargs.get('from_name') else None
        self.replay_to_id = kwargs.pop('replay_to_id') if kwargs.get('replay_to_id') else None
        self.replay_to_name = kwargs.pop('replay_to_name') if kwargs.get('replay_to_name') else None

        if kwargs.get('type') == 'telegram':
            self.__super = super(Message, self)
            self.__super.__init__(**kwargs)

    def __str__(self):
        return f"<Message type='{self.type}' from_name='{self.from_name}' text='{self.text}'>"

    def dump(self):
        dump = {}
        dump['type'] = self.type
        dump['text'] = self.text
        dump['from_id'] = self.from_id
        dump['from_name'] = self.from_name
        dump['replay_to_id'] = self.replay_to_id
        dump['replay_to_name'] = self.replay_to_name
        dump['token'] = self.token
        if self.type == 'telegram':
            dump['command'] = self.command
        json.dumps(dump)
        return json.dumps(dump)

    @staticmethod
    def load(dump):
        dump = json.loads(dump)
        kwargs = {}
        for cur in dump:
            if dump[cur]:
                kwargs[cur] = dump[cur]
        return Message(**kwargs)

    def get(self):
        return self.__super.get()

    def send(self):
        return self.__super.send()


if __name__ == '__main__':
    msg = Message(
        text=f'Привет!',
        replay_to_id=123123123,
        type='telegram',
        token='msg.token123123123123213'
    )
    print(msg)
    tmp = msg.dump()
    print(tmp)
    new_msg = Message.load(tmp)
    print(new_msg)
