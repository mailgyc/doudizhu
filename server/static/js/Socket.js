
PokerGame.Socket = {
    // wsUri: "ws://m.enjoygame.net:8000/socket",
    wsUri: "ws://127.0.0.1:8080/socket",
    websocket: null,
    onmessage: null
}

PokerGame.Socket.connect = function(onopen_callback, onerror_callback) {

    if (this.websocket != null) {
        return;
    }
    
    this.websocket = new WebSocket(this.wsUri);
    this.websocket.onopen = function(evt) {
        console.log("CONNECTED");
        if (onopen_callback) {
            onopen_callback();
        }
    };
    
    this.websocket.onerror = function(evt) { 
        console.log('CONNECT ERROR: ' + evt.data); 
        if (onerror_callback) {
            onerror_callback();   
        }
    }; 
    
    this.websocket.onclose = function(evt) {
        console.log("DISCONNECTED"); 
        this.websocket = null;
    };

    this.websocket.onmessage = function(evt) {
        console.log('RESPONSE: ' + evt.data);
        if (PokerGame.Socket.onmessage) {
            PokerGame.Socket.onmessage(JSON.parse(evt.data));
        }
    }; 
}  

PokerGame.Socket.send = function(msg) {
    this.websocket.send(JSON.stringify(msg));
}
