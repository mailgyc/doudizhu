import {Poker, Rule} from '/static/js/rule.mjs'
import {Player, createPlay} from '/static/js/player.mjs'
import {Protocol, Socket} from '/static/js/net.mjs'

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
        }
    }
}

const observer = new Observer();

export class Game {
    constructor(game) {
        this.players = [];

        this.tablePoker = [];
        this.tablePokerPic = {};

        this.lastShotPlayer = null;

        this.whoseTurn = 0;
    }

    init(baseScore) {
        observer.set('baseScore', baseScore);
    }

    create() {
        Rule.RuleList = this.cache.getJSON('rule');
        this.stage.backgroundColor = '#182d3b';

        this.players.push(createPlay(0, this));
        this.players.push(createPlay(1, this));
        this.players.push(createPlay(2, this));
        this.players[0].updateInfo(window.playerInfo.uid, window.playerInfo.name);
        const protocol = location.protocol.startsWith("https") ? "wss://" : "ws://";
        this.socket = new Socket(protocol + location.host + "/ws");
        this.socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));

        const width = this.game.world.width;
        const height = this.game.world.height;

        const titleBar = this.game.add.text(width / 2, 0, `房间号:${0} 底分: 0 倍数: 0`, {
            font: "22px",
            fill: "#fff",
            align: "center"
        });
        titleBar.anchor.set(0.5, 0);
        observer.subscribe('room', function (room) {
            titleBar.text = `房间号:${room.id} 底分: ${room.origin} 倍数: ${room.multiple}`;
        });

        // 创建准备按钮
        const that = this;
        const countdown = this.game.add.text(width / 2, height / 2, '10', {
            font: "80px",
            fill: "#fff",
            align: "center"
        });
        countdown.anchor.set(0.5);
        countdown.visible = false;
        observer.subscribe('countdown', function (timer) {
            countdown.visible = timer >= 0;
            if (timer >= 0) {
                countdown.text = timer;
                that.game.time.events.add(1000, function () {
                    observer.set('countdown', observer.get('countdown') - 1);
                }, that);
            }
        });

        const ready = this.game.make.button(width / 2, height * 0.6, "btn", function () {
            this.send_message([Protocol.REQ_READY, {"ready": 1}]);
            observer.set('countdown', 10);
        }, this, 'ready.png', 'ready.png', 'ready.png');
        ready.anchor.set(0.5, 0);
        this.game.world.add(ready);

        observer.subscribe('ready', function (is_ready) {
            ready.visible = !is_ready;
        });

        // 创建抢地主按钮
        const group = this.game.add.group();
        let pass = this.game.make.button(width * 0.4, height * 0.6, "btn", function () {
            this.game.add.audio('f_score_0').play();
            this.send_message([Protocol.REQ_CALL_SCORE, {"rob": 0}]);
        }, this, 'score_0.png', 'score_0.png', 'score_0.png');
        pass.anchor.set(0.5, 0);
        group.add(pass);

        const rob = this.game.make.button(width * 0.6, height * 0.6, "btn", function () {
            this.game.add.audio('f_score_1').play();
            this.send_message([Protocol.REQ_CALL_SCORE, {"rob": 1}]);
        }, this, 'score_1.png', 'score_1.png', 'score_1.png');
        rob.anchor.set(0.5, 0);
        group.add(rob);
        group.visible = false;

        observer.subscribe('rob', function (is_rob) {
            group.visible = is_rob;
            observer.set('countdown', -1);
        });
    }

    onopen() {
        console.log('socket onopen');
        this.socket.send([Protocol.REQ_ROOM_LIST, {}]);
        this.socket.send([Protocol.REQ_JOIN_ROOM, {"room": -1, "level": observer.get('baseScore')}]);
    }

    onerror() {
        console.log('socket onerror, try reconnect.');
        this.socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));
    }

    send_message(request) {
        this.socket.send(request);
    }

    onmessage(message) {
        const code = message[0], packet = message[1];
        switch (code) {
            case Protocol.RSP_ROOM_LIST:
                console.log(code, packet);
                break;
            case Protocol.RSP_JOIN_ROOM:
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
            case Protocol.RSP_READY:
                // TODO: 显示玩家已准备状态
                if (packet['uid'] === this.players[0].uid) {
                    observer.set('ready', true);
                }
                break;
            case Protocol.RSP_DEAL_POKER: {
                const playerId = packet['uid'];
                const pokers = packet['pokers'];
                this.dealPoker(pokers);
                this.whoseTurn = this.uidToSeat(playerId);
                this.startCallScore();
                break;
            }
            case Protocol.RSP_CALL_SCORE: {
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
            case Protocol.RSP_SHOT_POKER:
                this.handleShotPoker(packet);
                observer.set('room.multiple', packet['multiple']);
                break;
            case Protocol.RSP_GAME_OVER: {
                const winner = packet['winner'];
                const that = this;
                packet['players'].forEach(function (player) {
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
            // case Protocol.RSP_CHEAT:
            //     let seat = this.uidToSeat(packet[1]);
            //     this.players[seat].replacePoker(packet[2], 0);
            //     this.players[seat].reDealPoker();
            //     break;
            default:
                console.log("UNKNOWN PACKET:", packet)
        }
    }

    cleanWorld() {
        this.players.forEach(function (player) {
            player.cleanPokers();
            // player.uiLeftPoker.kill();
            player.uiHead.frameName = 'icon_farmer.png';
        });
        for (let i = 0; i < this.tablePoker.length; i++) {
            let p = this.tablePokerPic[this.tablePoker[i]];
            p.destroy();
        }
    }

    restart() {
        this.players = [];

        this.tablePoker = [];
        this.tablePokerPic = {};

        this.lastShotPlayer = null;

        this.whoseTurn = 0;

        this.stage.backgroundColor = '#182d3b';
        this.players.push(createPlay(0, this));
        this.players.push(createPlay(1, this));
        this.players.push(createPlay(2, this));
        for (let i = 0; i < 3; i++) {
            //this.players[i].uiHead.kill();
        }
    }

    update() {
    }

    uidToSeat(uid) {
        for (let i = 0; i < 3; i++) {
            if (uid === this.players[i].uid)
                return i;
        }
        console.log('ERROR uidToSeat:' + uid);
        return -1;
    }

    dealPoker(pokers) {
        // 添加一张底牌
        let p = new Poker(this, 55, 55);
        this.tablePokerPic[55] = p;
        this.game.world.add(p);

        for (let i = 0; i < 17; i++) {
            this.players[2].pokerInHand.push(55);
            this.players[1].pokerInHand.push(55);
            this.players[0].pokerInHand.push(pokers.pop());
        }

        this.players[0].dealPoker();
        this.players[1].dealPoker();
        this.players[2].dealPoker();
    }

    showLastThreePoker() {
        // 删除底牌
        this.tablePokerPic[55].destroy();
        delete this.tablePokerPic[55];

        for (let i = 0; i < 3; i++) {
            let pokerId = this.tablePoker[i];
            let p = new Poker(this, pokerId, pokerId);
            this.tablePokerPic[pokerId] = p;
            this.game.world.add(p);
            this.game.add.tween(p).to({x: this.game.world.width / 2 + (i - 1) * 60}, 600, Phaser.Easing.Default, true);
        }
        this.game.time.events.add(1500, this.dealLastThreePoker, this);
    }

    dealLastThreePoker() {
        let turnPlayer = this.players[this.whoseTurn];

        for (let i = 0; i < 3; i++) {
            let pid = this.tablePoker[i];
            let poker = this.tablePokerPic[pid]
            turnPlayer.pokerInHand.push(pid);
            turnPlayer.pushAPoker(poker);
        }
        turnPlayer.sortPoker();
        if (this.whoseTurn === 0) {
            turnPlayer.arrangePoker();
            const that = this;
            for (let i = 0; i < 3; i++) {
                let pid = this.tablePoker[i];
                let p = this.tablePokerPic[pid];
                let tween = this.game.add.tween(p).to({y: this.game.world.height - Poker.PH * 0.8}, 400, Phaser.Easing.Default, true);

                function adjust(p) {
                    that.game.add.tween(p).to({y: that.game.world.height - Poker.PH / 2}, 400, Phaser.Easing.Default, true, 400);
                }

                tween.onComplete.add(adjust, this, p);
            }
        } else {
            let first = turnPlayer.findAPoker(55);
            for (let i = 0; i < 3; i++) {
                let pid = this.tablePoker[i];
                let p = this.tablePokerPic[pid];
                p.frame = 55 - 1;
                this.game.add.tween(p).to({x: first.x, y: first.y}, 200, Phaser.Easing.Default, true);
            }
        }

        this.tablePoker = [];
        this.lastShotPlayer = turnPlayer;
        if (this.whoseTurn === 0) {
            this.startPlay();
        }
    }

    handleShotPoker(packet) {
        this.whoseTurn = this.uidToSeat(packet['uid']);
        let turnPlayer = this.players[this.whoseTurn];
        let pokers = packet['pokers'];
        if (pokers.length === 0) {
            this.players[this.whoseTurn].say("不出");
        } else {
            let pokersPic = {};
            pokers.sort(Poker.comparePoker);
            let count = pokers.length;
            let gap = Math.min((this.game.world.width - Poker.PW * 2) / count, Poker.PW * 0.36);
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
    }

    startCallScore() {
        if (this.whoseTurn === 0) {
            observer.set('rob', true);
        }

    }

    startPlay() {
        if (this.isLastShotPlayer()) {
            this.players[0].playPoker([]);
        } else {
            this.players[0].playPoker(this.tablePoker);
        }
    }

    finishPlay(pokers) {
        this.send_message([Protocol.REQ_SHOT_POKER, {"pokers": pokers}]);
    }

    isLastShotPlayer() {
        return this.players[this.whoseTurn] === this.lastShotPlayer;
    }

    quitGame() {
        this.state.start('MainMenu');
    }
}






