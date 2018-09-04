
PG.Protocol = {
    REQ_CHEAT : 1,
    RSP_CHEAT : 2,

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

    REQ_NEW_TABLE : 21,
    RSP_NEW_TABLE : 22,

    REQ_DEAL_POKER : 31,
    RSP_DEAL_POKER : 32,

    REQ_CALL_SCORE : 33,
    RSP_CALL_SCORE : 34,

    REQ_SHOW_POKER : 35,
    RSP_SHOW_POKER : 36,

    REQ_SHOT_POKER : 37,
    RSP_SHOT_POKER : 38,

    REQ_GAME_OVER : 41,
    RSP_GAME_OVER : 42,

    REQ_CHAT : 43,
    RSP_CHAT : 44
};

PG.Socket = {
    websocket: null,
    onmessage: null
};

PG.Socket.connect = function(onopen, onmessage, onerror) {

    if (this.websocket != null) {
        return;
    }
    
    this.websocket = new WebSocket("ws://" + window.location.host + "/ws");
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
        onmessage(JSON.parse(evt.data));
    };
};

PG.Socket.send = function(msg) {
    console.log('REQ: ' + msg);
    this.websocket.send(JSON.stringify(msg));
};
