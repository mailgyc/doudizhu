class Observer {

    constructor() {
        this.state = {};
        this.subscribers = {};
    }

    get(key) {
        return this.state[key];
    }

    publish(key, val) {
        this.state[key] = val;

        const subscribers = this.subscribers;
        if (subscribers.hasOwnProperty(key)) {
            subscribers[key].forEach(function (cb) {
                if (cb) cb(val);
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

    this.tableId = 0;

    this.tablePoker = [];
    this.tablePokerPic = {};

    this.lastShotPlayer = null;

    this.whoseTurn = 0;
};

PG.Game.prototype = {

    init: function (baseScore) {
        observer.publish('baseScore', baseScore);
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
            titleBar.text = `房间号:${room.id} 底分: ${room.base} 倍数: ${room.multiple}`;
        });

        const sx = this.game.world.width / 2;
        const sy = this.game.world.height * 0.6;
        let ready = this.game.make.button(sx, sy, "btn", function() {
            // this.restart();
            this.send_message([PG.Protocol.REQ_READY]);
        }, this, 'ready.png', 'ready.png', 'ready.png');
        ready.anchor.set(0.5, 0);
        this.game.world.add(ready);

        observer.subscribe('ready', function(is_ready) {
            ready.visible = !is_ready;
        })
    },

    onopen: function () {
        console.log('socket onopen');
        PG.Socket.send([PG.Protocol.REQ_JOIN_ROOM, -1, observer.get('baseScore')]);
    },

    onerror: function () {
        console.log('socket connect onerror');
    },

    send_message: function (request) {
        PG.Socket.send(request);
    },

    onmessage: function (packet) {
        const code = packet[0];
        switch (code) {
            case PG.Protocol.RSP_JOIN_ROOM:
                observer.publish('room', packet[1]['room']);
                const syncInfo = packet[1]['players'];
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
                observer.get('room').multiple = 15;
                observer.publish('ready', true);
                break;
            case PG.Protocol.RSP_DEAL_POKER: {
                const playerId = packet[1];
                const pokers = packet[2];
                console.log(pokers);
                this.dealPoker(pokers);
                this.whoseTurn = this.uidToSeat(playerId);
                this.startCallScore();
                break;
            }
            case PG.Protocol.RSP_CALL_SCORE: {
                const playerId = packet[1];
                const rob = packet[2];
                const isCallEnd = packet[3];
                this.whoseTurn = this.uidToSeat(playerId);

                const hanzi = ['不抢', "抢地主"];
                this.players[this.whoseTurn].say(hanzi[rob]);
                if (!isCallEnd) {
                    this.whoseTurn = (this.whoseTurn + 1) % 3;
                    this.startCallScore();
                }
                if (rob === 1) {
                    let room = observer.get('room');
                    room.multiple *= 2;
                    observer.publish('room', room)
                }
                break;
            }
            case PG.Protocol.RSP_SHOW_POKER:
                this.whoseTurn = this.uidToSeat(packet[1]);
                this.tablePoker[0] = packet[2][0];
                this.tablePoker[1] = packet[2][1];
                this.tablePoker[2] = packet[2][2];
                this.players[this.whoseTurn].setLandlord();
                this.showLastThreePoker();
                break;
            case PG.Protocol.RSP_SHOT_POKER:
                this.handleShotPoker(packet);
                break;
            case PG.Protocol.RSP_GAME_OVER:
                const gameResult = packet[1];
                const winner = gameResult.winner;
                const pokers = gameResult.pokers;

                let loserASeat = this.uidToSeat(pokers[0][0]);
                this.players[loserASeat].replacePoker(pokers[0], 1);
                this.players[loserASeat].reDealPoker();

                let loserBSeat = this.uidToSeat(pokers[1][0]);
                this.players[loserBSeat].replacePoker(pokers[1], 1);
                this.players[loserBSeat].reDealPoker();

                this.whoseTurn = this.uidToSeat(winner);
                function gameOver() {
                    alert(this.players[this.whoseTurn].isLandlord ? "地主赢" : "农民赢");
                    PG.Socket.send([PG.Protocol.REQ_RESTART]);
                    observer.publish('ready', false);
                    this.cleanWorld();
                }

                this.game.time.events.add(2000, gameOver, this);
                break;
            case PG.Protocol.RSP_CHEAT:
                let seat = this.uidToSeat(packet[1]);
                this.players[seat].replacePoker(packet[2], 0);
                this.players[seat].reDealPoker();
                break;
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
            if (uid == this.players[i].uid)
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
        //this.game.time.events.add(1000, function() {
        //    this.send_message([PG.Protocol.REQ_CHEAT, this.players[1].uid]);
        //    this.send_message([PG.Protocol.REQ_CHEAT, this.players[2].uid]);
        //}, this);
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
            for (let i = 0; i < 3; i++) {
                let p = this.tablePoker[i + 3];
                let tween = this.game.add.tween(p).to({y: this.game.world.height - PG.PH * 0.8}, 400, Phaser.Easing.Default, true);

                function adjust(p) {
                    this.game.add.tween(p).to({y: this.game.world.height - PG.PH / 2}, 400, Phaser.Easing.Default, true, 400);
                };
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
        this.whoseTurn = this.uidToSeat(packet[1]);
        let turnPlayer = this.players[this.whoseTurn];
        let pokers = packet[2];
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
        function btnTouch(btn) {
            this.send_message([PG.Protocol.REQ_CALL_SCORE, btn.score]);
            btn.parent.destroy();
            const audio = this.game.add.audio('f_score_' + btn.score);
            audio.play();
        }

        if (this.whoseTurn === 0) {
            const sy = this.game.world.height * 0.6;
            const group = this.game.add.group();
            let pass = this.game.make.button(this.game.world.width * 0.4, sy, "btn", btnTouch, this, 'score_0.png', 'score_0.png', 'score_0.png');
            pass.anchor.set(0.5, 0);
            pass.score = 0;
            group.add(pass);

            const rob = this.game.make.button(this.game.world.width * 0.6, sy, "btn", btnTouch, this, 'score_1.png', 'score_1.png', 'score_1.png');
            rob.anchor.set(0.5, 0);
            rob.score = 1;
            group.add(rob);
        } else {
            // TODO show clock on target
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
        this.send_message([PG.Protocol.REQ_SHOT_POKER, pokers]);
    },

    isLastShotPlayer: function () {
        return this.players[this.whoseTurn] == this.lastShotPlayer;
    },

    quitGame: function () {
        this.state.start('MainMenu');
    },

    onJoin: function (btn) {
        if (btn.tableId == -1) {
            this.send_message([PG.Protocol.REQ_NEW_TABLE]);
        } else {
            this.send_message([PG.Protocol.REQ_JOIN_TABLE, btn.tableId]);
        }
        btn.parent.destroy();
    }
};






