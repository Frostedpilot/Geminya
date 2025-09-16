class EventBus:
    """Central nervous system for game communication."""
    
    def __init__(self):
        self.subscribers = {}  # event_name -> list of handler functions
    
    def subscribe(self, event_name, handler_function):
        """Subscribe a handler function to an event."""
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(handler_function)
    
    def publish(self, event_name, data_payload=None):
        """Publish an event with optional data payload to all subscribers."""
        if event_name in self.subscribers:
            for handler in self.subscribers[event_name]:
                handler(data_payload)