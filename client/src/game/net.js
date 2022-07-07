
const Protocol = {
    CLI_CHEAT : 1,
    SER_CHEAT : 2,

    CLI_LOGIN : 11,
    SER_LOGIN : 12,

    CLI_LIST_TABLE : 15,
    SER_LIST_TABLE : 16,

    CLI_CREATE_TABLE : 17,
    SER_CREATE_TABLE : 18,

    CLI_JOIN_TABLE : 19,
    SER_JOIN_TABLE : 20,

    CLI_DEAL_POKER : 31,
    SER_DEAL_POKER : 32,

    CLI_CALL_SCORE : 33,
    SER_CALL_SCORE : 34,

    CLI_HOLE_POKER : 35,
    SER_HOLE_POKER : 36,

    CLI_SHOT_POKER : 37,
    SER_SHOT_POKER : 38,

    CLI_GAME_OVER : 41,
    SER_GAME_OVER : 42,

    CLI_CHAT : 43,
    SER_CHAT : 44,

    CLI_RESTART : 45,
    SER_RESTART : 46
};

class Socket {
    constructor() {
        this.websocket = null;
    }

    connect(onopen, onmessage, onerror) {

        if (this.websocket != null) {
            return;
        }

        const protocol = window.location.protocol.startsWith('https') ? 'wss://' : 'ws://';
        const host = window.location.host;
        this.websocket = new WebSocket(protocol + host + "/ws");
        this.websocket.binaryType = 'arraybuffer';
        this.websocket.onopen = function (evt) {
            console.log("CONNECTED");
            onopen();
        };

        this.websocket.onerror = function (evt) {
            console.log('CONNECT ERROR: ' + evt.data);
            this.websocket = null;
            onerror();
        };

        this.websocket.onclose = function (evt) {
            console.log("DISCONNECTED");
            this.websocket = null;
        };

        this.websocket.onmessage = function (evt) {
            console.log('RECV: ' + evt.data);
            onmessage(JSON.parse(evt.data));
        };
    }

    send(msg) {
        console.log('SEND: ' + msg);
        this.websocket.send(JSON.stringify(msg));
    }
}

export {Protocol, Socket}