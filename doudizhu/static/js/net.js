PG.Protocol = {
    /**
     * [ERROR, {"reason": 错误原因}]
     */
    ERROR: 0,

    /**
     * 请求房间列表
     * [REQ_ROOM_LIST, {}]
     */
    REQ_ROOM_LIST: 1001,
    /**
     * [RSP_ROOM_LIST, {
     *     "rooms": [{"level": int 房间等级, "number": int 房间人数}]
     * }]
     */
    RSP_ROOM_LIST: 1002,

    REQ_NEW_ROOM: 1003,
    RSP_NEW_ROOM: 1004,


    /**
     * 请求加入房间
     * [REQ_JOIN_ROOM, {"room": int 房间号 (-1表示快速加入), "level": int (1/2/3 初/中/高级场)}]
     *
     */
    REQ_JOIN_ROOM: 1005,
    /**
     *  用户进入房间广播
     *  [RSP_JOIN_ROOM, {
     *      "room": {
     *          "id": int 房间号,
     *          "origin": int 底分,
     *          "multiple": int 倍数,
     *          "state": int 房间状态 (1/2/3/4 WAITING/CALL_SCORE/PLAYING/GAME_OVER),
     *          "landlord_uid": int 本轮叫地主用户,
     *          "whose_turn": int 正在叫分/出牌用户 UID,
     *          "timer": int 倒计时,
     *          "last_shot_uid": int 房间状态,
     *          "last_shot_poker": int 房间状态,
     *      },
     *      "players": [{
     *          "uid": int 用户ID,
     *          "name": 用户名,
     *          "icon": 头像,
     *          "sex": int 0 男 1 女
     *          "point": int 分数
     *          "ready": int 是否准备(1 准备 0 未准备),
     *          "rob":  int 是否抢地主 (-1/0/1),
     *          "leave": int 是否离开房间 (1 离开离开 0 在房间)
     *          "landlord":  int 是否是地主 (0/1),
     *          "pokers": [int 手牌]
     *      }, {}, {}]
     *  }]
     */
    RSP_JOIN_ROOM: 1006,

    /**
     * 请求离开房间
     * [REQ_LEAVE_ROOM, {}]
     */
    REQ_LEAVE_ROOM: 1007,

    /**
     * 离开房间广播
     * [REQ_LEAVE_ROOM, {"uid": int 用户ID}]
     */
    RSP_LEAVE_ROOM: 1008,

    /**
     * 用户进入准备状态
     * [REQ_READY, {"ready": int (1 准备 0 取消准备)}]
     */
    REQ_READY: 2001,
    /**
     * 用户准备/取消准备状态广播
     * [RSP_READY, {"uid": 用户ID, "ready": int(0/1)}]
     */
    RSP_READY: 2002,


    /**
     *  发牌, 当用户全部进去准备状态，服务器主动下发
     *  [RSP_DEAL_POKER, {
     *      "room_id": 用户ID 开始抢地主的用户, 客户端判断是否是自己,
     *      "timer": int 倒计时开始,
     *      "pokers": [int 17张扑克牌]
     *  }]
     */
    RSP_DEAL_POKER: 2004,


    /**
     *  是否抢地主
     *  [REQ_CALL_SCORE, {"rob": int (0 不抢  1 抢地主)}]
     */
    REQ_CALL_SCORE: 2005,

    /**
     * 抢地主广播
     * [RSP_CALL_SCORE, {
     *      "room_id": 叫地主用户ID,
     *      "rob": int 是否抢地主,
     *      "landlord": 用户ID, -1表示继续抢地主, 否则返回地主用户ID,
     *      "multiple": int 当前倍数,
     *      "pokers": [int 抢地主结束时返回三张底牌]}
     *      }]
     */
    RSP_CALL_SCORE: 2006,


    /**
     * 请求出牌
     * [REQ_SHOT_POKER, {"pokers": [int 扑克牌]}]
     */
    REQ_SHOT_POKER: 3001,
    /**
     * 出牌广播
     *  [RSP_SHOT_POKER, {"uid": 用户ID 出牌用户, "pokers": [int 扑克牌], "multiple": int 当前倍数}]
     */
    RSP_SHOT_POKER: 3002,


    /**
     *  游戏结束广播, 服务器主动下发
     *  pokers 为最后展示手牌用, 可以忽略
     *  [RSP_GAME_OVER, {
     *      "winner": int 获胜的用户ID,
     *      "spring": int 是否春天 1/0,
     *      "antispring": int 是否反春 1/0,
     *      "multiple": {
     *         "origin": int 初始倍数,
     *         "di": int   底牌,
     *         "ming": int 明牌,
     *         "bomb": int 炸弹,
     *         "rob": int  抢地主,
     *         "spring": int 春天,
     *         "landlord": int 地主加倍,
     *         "farmer": int 农民加倍
     *      },
     *      "players": [{"uid": int用户ID, "point": int 输赢分数, "pokers": [int 手牌]}, {}, {}],
     *  }]
     */
    RSP_GAME_OVER: 4002,
};

PG.Socket = {
    websocket: null,
    onmessage: null
};

const logging_pretty = function (tag, packet) {
    for (let key in PG.Protocol) {
        if (packet[0] === PG.Protocol[key])
            console.log(`${tag}: ${key} ${JSON.stringify(packet.slice(1))}`)
    }
};

PG.Socket.connect = function (onopen, onmessage, onerror) {

    if (this.websocket != null) {
        return;
    }

    const protocol = location.protocol.startsWith("https") ? "wss://" : "ws://";
    this.websocket = new WebSocket(protocol + location.host + "/ws");
    this.websocket.binaryType = "arraybuffer";
    this.websocket.onopen = function (evt) {
        console.log("CONNECTED");
        onopen();
    };

    this.websocket.onerror = function (evt) {
        console.log("CONNECT ERROR: " + evt.data);
        this.websocket = null;
        onerror();
    };

    this.websocket.onclose = function (evt) {
        console.log("DISCONNECTED");
        this.websocket = null;
        onerror();
    };

    this.websocket.onmessage = function (evt) {
        const packet = JSON.parse(evt.data);
        logging_pretty("RSP", packet);
        onmessage(packet);
    };
};

PG.Socket.send = function (packet) {
    logging_pretty("REQ", packet);
    this.websocket.send(JSON.stringify(packet));
};
