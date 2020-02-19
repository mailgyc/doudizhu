
PG.Protocol = {
    REQ_CHEAT : 1,
    RSP_CHEAT : 2,

    REQ_LOGIN : 11,
    RSP_LOGIN : 12,

    REQ_ROOM_LIST  : 13,
    RSP_ROOM_LIST  : 14,

    REQ_NEW_ROOM : 15,
    RSP_NEW_ROOM : 16,


    // 请求加入房间 [REQ_JOIN_ROOM, 房间号] -1 表示快速加入
    REQ_JOIN_ROOM : 17,
    /**
     *  返回房间状态, 每有新玩家加入就会返回
     *  [RSP_JOIN_ROOM, {
     *      'room': {"id": 房间号, "base": 底分, "multiple": 倍数},
     *      'player': [{"uid": 用户ID, "name": 用户名, "icon": 头像, "ready": int}, {}, {}]
     *  }]
     */
    RSP_JOIN_ROOM : 18,


    // 点击准备按钮 [REQ_READY, 1/0]  1 准备  0取消准备
    REQ_READY : 21,
    // 返回 [RSP_READY, {"uid": 用户ID, "ready": int(0/1)}]
    RSP_READY : 22,


    REQ_DEAL_POKER : 31,
    /**
     *  发牌, 当玩家全部准备就绪，服务器主动下发
     *  [RSP_DEAL_POKER, {
     *      "uid": 用户ID 开始抢地主的玩家, 客户端判断是否是自己,
     *      "pokers": [int 17张扑克牌]
     *  }]
     */
    RSP_DEAL_POKER : 32,


    /**
     *  是否叫地主
     *  [REQ_CALL_SCORE, 0/1]  0 不叫  1 叫
     */
    REQ_CALL_SCORE : 33,

    /**
     *  用户ID 为地主玩家, 客户端更新地主头像
     * [RSP_CALL_SCORE, {
     *      "uid": 叫地主用户ID,
     *      "rob": int(0/1) 是否叫地主,
     *      "landlord": 用户ID, -1表示继续抢地主, 否则返回地主用户ID
     *      "pokers": [int 三张底牌]}
     *      }]
     */
    RSP_CALL_SCORE : 34,


    /**
     * 出牌, 客户端应收到 RSP_SHOT_POKER 后做出牌动画
     * [REQ_SHOT_POKER, [int 扑克牌]]
     */
    REQ_SHOT_POKER : 37,
    /**
     *  用户ID 为出牌玩家
     *  [RSP_SHOT_POKER, {'uid': 用户ID, 'pokers': [int 扑克牌]}]
     */
    RSP_SHOT_POKER : 38,


    REQ_GAME_OVER : 41,
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

    var protocol = location.protocol.startsWith('https') ? 'wss://' : 'ws://';
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
