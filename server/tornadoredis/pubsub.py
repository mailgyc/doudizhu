import json
from collections import defaultdict
from collections import Counter
from tornado import stack_context


class BaseSubscriber(object):
    """
    A helper class to handle Pub/Sub subscriptions
    using a single redis connection.

    Override the on_message method or use the SockJSPubSub or SocketIOPubSub
    class in your application.
    """
    def __init__(self, tornado_redis_client):
        self.redis = tornado_redis_client
        self.subscribers = defaultdict(Counter)
        self.subscriber_count = Counter()

    def subscribe(self, channel_name, subscriber, callback=None):
        """
        Subscribes a given subscriber object to a redis channel.
        Does nothing if subscribe calls are nested for the
        same subscriber object.

        The broadcast method of the subscriber object will be called
        for each message received from specified channel.
        Override the on_message method to change this behaviour.

        Arguments:
        channel_name - channel name or list or tuple of channel names to subscribe for
        subscriber - a method or object to be used by on_message handler
        callback - a callback function
        """
        if isinstance(channel_name, list) or isinstance(channel_name, tuple):
            if len(channel_name) > 1:
                _cb = lambda *args, **kwargs: self.subscribe(channel_name[1:],
                                                             subscriber,
                                                             callback=callback)
            else:
                _cb = callback
            self.subscribe(channel_name[0], subscriber, callback=_cb)
        else:
            self.subscribers[channel_name][subscriber] += 1
            self.subscriber_count[channel_name] += 1
            if self.subscriber_count[channel_name] == 1:
                if not self.redis.subscribed:
                    if callback:
                        callback = stack_context.wrap(callback)

                    def _cb(*args, **kwargs):
                        self.redis.listen(self.on_message)
                        if callback:
                            callback(*args, **kwargs)

                    cb = _cb
                else:
                    cb = callback
                self.redis.subscribe(channel_name, callback=cb)
            elif callback:
                callback(True)

    def unsubscribe(self, channel_name, subscriber):
        """
        Unsubscribes a subscriber from the redis channel.

        Unsubscribes the redis client from the channel
        if there are no subscribers left.
        """
        self.subscribers[channel_name][subscriber] -= 1
        if self.subscribers[channel_name][subscriber] <= 0:
            del self.subscribers[channel_name][subscriber]
        self.subscriber_count[channel_name] -= 1
        if self.subscriber_count[channel_name] <= 0:
            del self.subscriber_count[channel_name]
            self.redis.unsubscribe(channel_name)

    def on_message(self, msg):
        """
        Handles a message posted to the Redis channel.

        Broadcasts JSON-encoded message to end users using
        the SockJSConnection.broadcast method.

        Override this method if needed.
        """
        if not msg:
            return

        if msg.kind == 'disconnect':
            # Disconnected from the Redis server
            # Close the redis connection
            self.close()

    def publish(self, channel_name, data, client=None, callback=None):
        """
        Publishes a message to the redis channel.

        Use a different client instance if you ever need to publish something
        in your application.
        """
        data = json.dumps(data) if data is not None else ''
        (client or self.redis).publish(channel_name, data, callback=callback)

    def close(self):
        """
        Unsubscribes the redis client from all subscriber.
        Clears subscriber lists and counters.
        """
        for channel_name, subscribers in list(self.subscriber_count.items()):
            if subscribers and self.redis.connection.connected():
                self.redis.unsubscribe(channel_name)
        self.subscribers = defaultdict(Counter)
        self.subscriber_count = Counter()

    def is_subscribed(self):
        """
        Returns True if subscribed to any channel.
        """
        for channel_name, subscribers in list(self.subscriber_count.items()):
            if subscribers:
                return True
        return False


class SockJSSubscriber(BaseSubscriber):
    """
    Use this class to send messages from the redis channel directly to
    subscribers via SockJS connection.

    The on_message handler utilizes the SockJSConnection.broadcast method.
    """
    def on_message(self, msg):
        if not msg:
            return
        if msg.kind == 'message' and msg.body:
            # Get the list of subscribers for this channel
            subscribers = list(self.subscribers[msg.channel].keys())
            if subscribers:
                # Use the first active subscriber/client connection
                # for broadcasting. Thanks to Jonas Hagstedt
                for s in subscribers:
                    if not s.session.is_closed:
                        s.broadcast(subscribers, msg.body)
                        break
        super(SockJSSubscriber, self).on_message(msg)


class SocketIOSubscriber(BaseSubscriber):
    """
    Use this class to send messages from the redis channel directly to
    subscribers via SocketIO connection (thanks to Ofir Herzas)
    """
    def on_message(self, msg):
        if not msg:
            return
        if msg.kind == 'message' and msg.body:
            # Get the list of subscribers for this channel
            subscribers = list(self.subscribers[msg.channel].keys())
            if subscribers:
                for subscriber in subscribers:
                    subscriber.on_message(msg.body)
        super(SocketIOSubscriber, self).on_message(msg)
