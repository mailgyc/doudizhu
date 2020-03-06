class Observer {

    constructor() {
        this.state = {};
        this.subscribers = {};
    }

    get(key) {
        return this.state[key];
    }

    set(key, val) {
        const keys = key.split('.');
        if (keys.length === 1) {
            this.state[key] = val;
        } else {
            this.state[keys[0]][keys[1]] = val;
            key = keys[0];
        }
        const newVal = this.state[key];
        const subscribers = this.subscribers;
        if (subscribers.hasOwnProperty(key)) {
            subscribers[key].forEach(function (cb) {
                if (cb) cb(newVal);
            });
        }
    }

    subscribe(key, cb) {
        const subscribers = this.subscribers;
        if (subscribers.hasOwnProperty(key)) {
            subscribers[key].push(cb);
        } else {
            subscribers[key] = [cb];
        }
    }

    unsubscribe(key, cb) {
        const subscribers = this.subscribers;
        if (subscribers.hasOwnProperty(key)) {
            const index = subscribers.indexOf(cb);
            if (index > -1) {
                subscribers.splice(index, 1);
            }
        } else {
            subscribers[key] = [cb];
        }
    }
}

const observer = new Observer();

PG.Game = function (game) {
    this.players = [];

    this.tablePoker = [];
    this.tablePokerPic = {};

    this.lastShotPlayer = null;

    this.whoseTurn = 0;
};

PG.Game.prototype = {

    init: function (baseScore) {
        observer.set('baseScore', baseScore);
    },

    create: function () {
        this.stage.backgroundColor = '#182d3b';

        this.players.push(PG.createPlay(0, this));
        this.players.push(PG.createPlay(1, this));
        this.players.push(PG.createPlay(2, this));
        this.players[0].updateInfo(PG.playerInfo.uid, PG.playerInfo.username);
        PG.Socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));

        let style = {font: "22px Arial", fill: "#fff", align: "center"};
        let titleBar = this.game.add.text(this.game.world.centerX, 0, `房间号:${0} 底分: 0 倍数: 0`, style);
        titleBar.anchor.set(0.5, 0);
        observer.subscribe('room', function (room) {
            titleBar.text = `房间号:${room.id} 底分: ${room.origin} 倍数: ${room.multiple}`;
        });

        // 创建准备按钮
        const sx = this.game.world.width / 2;
        const sy = this.game.world.height * 0.6;

        let ready = this.game.make.button(sx, sy, "btn", function() {
            this.send_message([PG.Protocol.REQ_READY, {"ready": 1}]);
        }, this, 'ready.png', 'ready.png', 'ready.png');
        ready.anchor.set(0.5, 0);
        this.game.world.add(ready);

        observer.subscribe('ready', function(is_ready) {
            ready.visible = !is_ready;
        });

        // 创建抢地主按钮
        const group = this.game.add.group();
        let pass = this.game.make.button(this.game.world.width * 0.4, sy, "btn", function () {
            this.game.add.audio('f_score_0').play();
            this.send_message([PG.Protocol.REQ_CALL_SCORE, {"rob": 0}]);
        }, this, 'score_0.png', 'score_0.png', 'score_0.png');
        pass.anchor.set(0.5, 0);
        group.add(pass);

        const rob = this.game.make.button(this.game.world.width * 0.6, sy, "btn", function() {
            this.game.add.audio('f_score_1').play();
            this.send_message([PG.Protocol.REQ_CALL_SCORE, {"rob": 1}]);
        }, this, 'score_1.png', 'score_1.png', 'score_1.png');
        rob.anchor.set(0.5, 0);
        group.add(rob);
        group.visible = false;

        observer.subscribe('rob', function(is_rob) {
            group.visible = is_rob;
        });
    },

    onopen: function () {
        console.log('socket onopen');
        PG.Socket.send([PG.Protocol.REQ_ROOM_LIST, {}]);
        PG.Socket.send([PG.Protocol.REQ_JOIN_ROOM, {"room": -1, "level": observer.get('baseScore')}]);
    },

    onerror: function () {
        console.log('socket onerror, try reconnect.');
        PG.Socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));
    },

    send_message: function (request) {
        PG.Socket.send(request);
    },

    onmessage: function (message) {
        const code = message[0], packet = message[1];
        switch (code) {
            case PG.Protocol.RSP_ROOM_LIST:
                console.log(code, packet);
                break;
            case PG.Protocol.RSP_JOIN_ROOM:
                observer.set('room', packet['room']);
                const syncInfo = packet['players'];
                for (let i = 0; i < syncInfo.length; i++) {
                    if (syncInfo[i].uid === this.players[0].uid) {
                        let info_1 = syncInfo[(i + 1) % 3];
                        let info_2 = syncInfo[(i + 2) % 3];
                        this.players[1].updateInfo(info_1.uid, info_1.name);
                        this.players[2].updateInfo(info_2.uid, info_2.name);
                        break;
                    }
                }
                break;
            case PG.Protocol.RSP_READY:
                // TODO: 显示玩家已准备状态
                if (packet['uid'] === this.players[0].uid) {
                    observer.set('ready', true);
                }
                break;
            case PG.Protocol.RSP_DEAL_POKER: {
                const playerId = packet['uid'];
                const pokers = packet['pokers'];
                this.dealPoker(pokers);
                this.whoseTurn = this.uidToSeat(playerId);
                this.startCallScore();
                break;
            }
            case PG.Protocol.RSP_CALL_SCORE: {
                const playerId = packet['uid'];
                const rob = packet['rob'];
                const landlord = packet['landlord'];
                this.whoseTurn = this.uidToSeat(playerId);

                const hanzi = ['不抢', "抢地主"];
                this.players[this.whoseTurn].say(hanzi[rob]);

                observer.set('rob', false);
                if (landlord === -1) {
                    this.whoseTurn = (this.whoseTurn + 1) % 3;
                    this.startCallScore();
                } else {
                    this.whoseTurn = this.uidToSeat(landlord);
                    this.tablePoker[0] = packet['pokers'][0];
                    this.tablePoker[1] = packet['pokers'][1];
                    this.tablePoker[2] = packet['pokers'][2];
                    this.players[this.whoseTurn].setLandlord();
                    this.showLastThreePoker();
                }
                observer.set('room.multiple', packet['multiple']);
                break;
            }
            case PG.Protocol.RSP_SHOT_POKER:
                this.handleShotPoker(packet);
                observer.set('room.multiple', packet['multiple']);
                break;
            case PG.Protocol.RSP_GAME_OVER: {
                const winner = packet['winner'];
                const that = this;
                packet['players'].forEach(function(player){
                    const seat = that.uidToSeat(player['uid']);
                    if (seat > 0) {
                        that.players[seat].replacePoker(player['pokers'], 0);
                        that.players[seat].reDealPoker();
                    }
                });

                this.whoseTurn = this.uidToSeat(winner);
                function gameOver() {
                    alert(that.players[that.whoseTurn].isLandlord ? "地主赢" : "农民赢");
                    observer.set('ready', false);
                    this.cleanWorld();
                }
                this.game.time.events.add(2000, gameOver, this);
                break;
            }
            // case PG.Protocol.RSP_CHEAT:
            //     let seat = this.uidToSeat(packet[1]);
            //     this.players[seat].replacePoker(packet[2], 0);
            //     this.players[seat].reDealPoker();
            //     break;
            default:
                console.log("UNKNOWN PACKET:", packet)
        }
    },

    cleanWorld: function () {
        this.players.forEach(function(player) {
            player.cleanPokers();
            // player.uiLeftPoker.kill();
            player.uiHead.frameName = 'icon_farmer.png';
        });
        for (let i = 0; i < this.tablePoker.length; i++) {
            let p = this.tablePokerPic[this.tablePoker[i]];
            p.destroy();
        }
    },

    restart: function () {
        this.players = [];

        this.tablePoker = [];
        this.tablePokerPic = {};

        this.lastShotPlayer = null;

        this.whoseTurn = 0;

        this.stage.backgroundColor = '#182d3b';
        this.players.push(PG.createPlay(0, this));
        this.players.push(PG.createPlay(1, this));
        this.players.push(PG.createPlay(2, this));
        for (let i = 0; i < 3; i++) {
            //this.players[i].uiHead.kill();
        }
    },

    update: function () {
    },

    uidToSeat: function (uid) {
        for (let i = 0; i < 3; i++) {
            if (uid === this.players[i].uid)
                return i;
        }
        console.log('ERROR uidToSeat:' + uid);
        return -1;
    },

    dealPoker: function (pokers) {

        for (let i = 0; i < 3; i++) {
            let p = new PG.Poker(this, 55, 55);
            this.game.world.add(p);
            this.tablePoker[i] = p.id;
            this.tablePoker[i + 3] = p;
        }

        for (let i = 0; i < 17; i++) {
            this.players[2].pokerInHand.push(55);
            this.players[1].pokerInHand.push(55);
            this.players[0].pokerInHand.push(pokers.pop());
        }

        this.players[0].dealPoker();
        this.players[1].dealPoker();
        this.players[2].dealPoker();
    },

    showLastThreePoker: function () {
        for (let i = 0; i < 3; i++) {
            let pokerId = this.tablePoker[i];
            let p = this.tablePoker[i + 3];
            p.id = pokerId;
            p.frame = pokerId - 1;
            this.game.add.tween(p).to({x: this.game.world.width / 2 + (i - 1) * 60}, 600, Phaser.Easing.Default, true);
        }
        this.game.time.events.add(1500, this.dealLastThreePoker, this);
    },

    dealLastThreePoker: function () {
        let turnPlayer = this.players[this.whoseTurn];

        for (let i = 0; i < 3; i++) {
            let pid = this.tablePoker[i];
            let poker = this.tablePoker[i + 3];
            turnPlayer.pokerInHand.push(pid);
            turnPlayer.pushAPoker(poker);
        }
        turnPlayer.sortPoker();
        if (this.whoseTurn === 0) {
            turnPlayer.arrangePoker();
            const that = this;
            for (let i = 0; i < 3; i++) {
                let p = this.tablePoker[i + 3];
                let tween = this.game.add.tween(p).to({y: this.game.world.height - PG.PH * 0.8}, 400, Phaser.Easing.Default, true);

                function adjust(p) {
                    that.game.add.tween(p).to({y: that.game.world.height - PG.PH / 2}, 400, Phaser.Easing.Default, true, 400);
                }
                tween.onComplete.add(adjust, this, p);
            }
        } else {
            let first = turnPlayer.findAPoker(54);
            for (let i = 0; i < 3; i++) {
                let p = this.tablePoker[i + 3];
                p.frame = 55 - 1;
                p.frame = 55 - 1;
                this.game.add.tween(p).to({x: first.x, y: first.y}, 200, Phaser.Easing.Default, true);
            }
        }

        this.tablePoker = [];
        this.lastShotPlayer = turnPlayer;
        if (this.whoseTurn === 0) {
            this.startPlay();
        }
    },

    handleShotPoker: function (packet) {
        this.whoseTurn = this.uidToSeat(packet['uid']);
        let turnPlayer = this.players[this.whoseTurn];
        let pokers = packet['pokers'];
        if (pokers.length === 0) {
            this.players[this.whoseTurn].say("不出");
        } else {
            let pokersPic = {};
            pokers.sort(PG.Poker.comparePoker);
            let count = pokers.length;
            let gap = Math.min((this.game.world.width - PG.PW * 2) / count, PG.PW * 0.36);
            for (let i = 0; i < count; i++) {
                let p = turnPlayer.findAPoker(pokers[i]);
                p.id = pokers[i];
                p.frame = pokers[i] - 1;
                p.bringToTop();
                this.game.add.tween(p).to({
                    x: this.game.world.width / 2 + (i - count / 2) * gap,
                    y: this.game.world.height * 0.4
                }, 500, Phaser.Easing.Default, true);

                turnPlayer.removeAPoker(pokers[i]);
                pokersPic[p.id] = p;
            }

            for (let i = 0; i < this.tablePoker.length; i++) {
                let p = this.tablePokerPic[this.tablePoker[i]];
                // p.kill();
                p.destroy();
            }
            this.tablePoker = pokers;
            this.tablePokerPic = pokersPic;
            this.lastShotPlayer = turnPlayer;
            turnPlayer.arrangePoker();
        }
        if (turnPlayer.pokerInHand.length > 0) {
            this.whoseTurn = (this.whoseTurn + 1) % 3;
            if (this.whoseTurn === 0) {
                this.game.time.events.add(1000, this.startPlay, this);
            }
        }
    },

    startCallScore: function () {
        if (this.whoseTurn === 0) {
            observer.set('rob', true);
        }

    },

    startPlay: function () {
        if (this.isLastShotPlayer()) {
            this.players[0].playPoker([]);
        } else {
            this.players[0].playPoker(this.tablePoker);
        }
    },

    finishPlay: function (pokers) {
        this.send_message([PG.Protocol.REQ_SHOT_POKER, {"pokers": pokers}]);
    },

    isLastShotPlayer: function () {
        return this.players[this.whoseTurn] === this.lastShotPlayer;
    },

    quitGame: function () {
        this.state.start('MainMenu');
    }
};






