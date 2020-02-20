
PG.Protocol = {
    /**
     * [ERROR, {"reason": 错误原因}]
     */
    ERROR: 0,

    REQ_CHEAT : 1,
    RSP_CHEAT : 2,

    REQ_LOGIN : 11,
    RSP_LOGIN : 12,

    REQ_ROOM_LIST  : 13,
    RSP_ROOM_LIST  : 14,

    REQ_NEW_ROOM : 15,
    RSP_NEW_ROOM : 16,


    /**
     * 请求加入房间
     * [REQ_JOIN_ROOM, {"room": int 房间号 (-1表示快速加入), "level": int (1/2/3 初/中/高级场)}]
     *
     */
    REQ_JOIN_ROOM : 17,
    /**
     *  返回房间状态, 每有新玩家加入就会通知
     *  [RSP_JOIN_ROOM, {
     *      'room': {
     *          "id": int 房间号,
     *          "base": int 底分,
     *          "multiple": int 倍数,
     *          "state": int 房间状态 (1/2/3/4 WAITING/CALL_SCORE/PLAYING/GAME_OVER),
     *          "landlord_uid": int 本轮叫地主玩家,
     *          "whose_turn": int 正在叫分/出牌玩家 UID,
     *          "timer": int 倒计时,
     *          "last_shot_uid": int 房间状态,
     *          "last_shot_poker": int 房间状态,
     *      },
     *      'player': [{
     *          "uid": 用户ID,
     *          "seat": 用户座位,
     *          "name": 用户名,
     *          "icon": 头像,
     *          "ready": int 是否准备(1 准备 0 未准备),
     *          "rob":  int 是否抢地主 (-1/0/1),
     *          "landlord":  int 是否是地主 (0/1),
     *      }, {}, {}]
     *  }]
     */
    RSP_JOIN_ROOM : 18,

    /**
     * 点击准备按钮 [REQ_READY, {"ready": int (1 准备 0 取消准备)}]
     */
    REQ_READY : 21,
    /**
     * 通知有玩家进入/取消准备状态
     * [RSP_READY, {"uid": 用户ID, "ready": int(0/1)}]
     */
    RSP_READY : 22,


    /**
     *  发牌, 当玩家全部准备就绪，服务器主动下发
     *  [RSP_DEAL_POKER, {
     *      "uid": 用户ID 开始抢地主的玩家, 客户端判断是否是自己,
     *      "timer": int 倒计时开始,
     *      "pokers": [int 17张扑克牌]
     *  }]
     */
    RSP_DEAL_POKER : 32,


    /**
     *  是否抢地主
     *  [REQ_CALL_SCORE, {"rob": int (0 不抢  1 抢地主)}]
     */
    REQ_CALL_SCORE : 33,

    /**
     * [RSP_CALL_SCORE, {
     *      "uid": 叫地主用户ID,
     *      "rob": int 是否抢地主,
     *      "landlord": 用户ID, -1表示继续抢地主, 否则返回地主用户ID
     *      "pokers": [int 抢地主结束时返回三张底牌]}
     *      }]
     */
    RSP_CALL_SCORE : 34,


    /**
     * [REQ_SHOT_POKER, {"pokers": [int 扑克牌]}]
     */
    REQ_SHOT_POKER : 37,
    /**
     *  [RSP_SHOT_POKER, {'uid': 用户ID 出牌玩家, 'pokers': [int 扑克牌]}]
     */
    RSP_SHOT_POKER : 38,


    /**
     *  游戏结束, 服务器主动下发
     *  pokers 为最后展示手牌用, 可以忽略
     *  [RSP_GAME_OVER, {
     *      "winner": 获胜的用户ID,
     *      "won_point": 赢了多少分,
     *      "lost_point": 输了多少分,
     *      "pokers": [[用户ID, 玩家剩的牌], [用户ID， 玩家剩的牌]],
     *  }]
     */
    RSP_GAME_OVER : 42,
};

PG.Socket = {
    websocket: null,
    onmessage: null
};

const logging_pretty = function(tag, packet) {
    for (key in PG.Protocol) {
        if (packet[0] === PG.Protocol[key])
            console.log(`${tag}: ${key} ${packet.slice(1)}`)
    }
};

PG.Socket.connect = function(onopen, onmessage, onerror) {

    if (this.websocket != null) {
        return;
    }

    const protocol = location.protocol.startsWith('https') ? 'wss://' : 'ws://';
    this.websocket = new WebSocket(protocol + location.host + "/ws");
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
        const packet = JSON.parse(evt.data);
        logging_pretty('RSP', packet);
        onmessage(packet);
    };
};

PG.Socket.send = function(packet) {
    logging_pretty('REQ', packet);
    this.websocket.send(JSON.stringify(packet));
};
