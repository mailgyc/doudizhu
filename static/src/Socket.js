
PokerGame.Socket = {
    wsUri: "ws://127.0.0.1:8000/socket",
    websocket: null
}

PokerGame.Socket.connect = function() {

    this.websocket = new WebSocket(this.wsUri);
    this.websocket.onopen = function(evt) {
        console.log("CONNECTED");
        PokerGame.Socket.write('["hello world"]');
    };
    this.websocket.onclose = function(evt) {
        console.log("DISCONNECTED"); 
    };

    this.websocket.onmessage = function(evt) {
        PokerGame.Socket.read(evt.data);
    }; 

    this.websocket.onerror = function(evt) { 
        console.log('ERROR: ' + evt.data); 
    }; 
}  

PokerGame.Socket.write = function(msg) {
    this.websocket.send(msg);
}


PokerGame.Socket.read = function(msg) {
    console.log('RESPONSE: ' + msg);
    //this.websocket.close(); 
}
