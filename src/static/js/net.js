
PG.Protocol = {
    REQ_LOGIN : 11,
    RSP_LOGIN : 12,

    REQ_ROOM_LIST  : 13,
    RSP_ROOM_LIST  : 14,

    REQ_TABLE_LIST : 15,
    RSP_TABLE_LIST : 16,

    REQ_JOIN_ROOM : 17,
    RSP_JOIN_ROOM : 18,

    REQ_JOIN_TABLE : 19,
    RSP_JOIN_TABLE : 20,

    REQ_DEAL_POKER : 21,
    RSP_DEAL_POKER : 22,

    REQ_CALL_SCORE : 23,
    RSP_CALL_SCORE : 24,

    REQ_SHOW_POKER : 25,
    RSP_SHOW_POKER : 26,

    REQ_SHOT_POKER : 31,
    RSP_SHOT_POKER : 32,

    REQ_GAME_OVER : 41,
    RSP_GAME_OVER : 42,

    REQ_CHAT : 43,
    RSP_CHAT : 44
};

PG.Socket = {
    wsUri: "ws://127.0.0.1:8080/ws",
    websocket: null,
    onmessage: null
};

PG.Socket.connect = function(onopen, onmessage, onerror) {

    if (this.websocket != null) {
        return;
    }
    
    this.websocket = new WebSocket(this.wsUri);
    this.websocket.binaryType = 'arraybuffer';
    this.websocket.onopen = function(evt) {
        console.log("CONNECTED");
        onopen();
    };
    
    this.websocket.onerror = function(evt) { 
        console.log('CONNECT ERROR: ' + evt.data); 
        onerror();
    };
    
    this.websocket.onclose = function(evt) {
        console.log("DISCONNECTED"); 
        this.websocket = null;
    };

    this.websocket.onmessage = function(evt) {
        console.log('RSP: ' + evt.data);
        // onmessage(msgpack.decode(evt.data));
        onmessage(JSON.parse(evt.data));
    };
};

PG.Socket.send = function(msg) {
    console.log('REQ: ' + msg);
    this.websocket.send(msgpack.encode(msg));
    // this.websocket.send(JSON.stringify(msg));
};
