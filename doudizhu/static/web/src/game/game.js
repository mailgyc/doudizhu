import Phaser from "phaser";
import Player from "./player"
import Poker from "./poker"
import {Protocol, Socket} from "./net";
import {SER_CHAT, SER_CREATE_TABLE, SER_DEAL_POKER, store, subscribe} from './store';

const PW = 90;
const PH = 120;

class GameScene extends Phaser.Scene {

    constructor() {
        super("GameScene");
        this.tablePokerPic = {};
        this.lastShotPlayer = null;
        this.whoseTurn = 0;
        this.RuleList = this.cache.json['rule'];
    }

    create() {
        // this.stage.backgroundColor = '#182d3b';
        // Socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));
        this.players = [new Player(0), new Player(1), new Player(2)];
        this.createRoom();
        this.createHead();
        this.createPoker();
    }

    createRoom() {
        const style = {fontSize: "22px", color: "#fff", align: "center"};
        let titleBar = this.add.text(this.game.config.width / 2, 0, '房间:', style);
        subscribe('room.tid', state => {
            titleBar.text = '房间号: ' + state.tableId;
        })
    }

    createHead() {
        // 下左 上左 上右
        const coords = [
            [PW / 2, this.game.config.height - 80],
            [this.game.config.width - PW / 2, 94 + 40],
            [PW / 2, 94 + 40],
        ];

        coords.forEach((coord, index) => {
            let head = this.add.sprite(coord[0], coord[1], 'ui', 'icon_default.png');
            head.setOrigin(0.5, 1);

            const style = {font: "22px", color: "#fff", align: "center"};
            let sayUI = this.add.text(head.x + head.width/2 + 10, head.y - head.height/2, '', style);

            const key = 'players.p' + index;
            subscribe(key, state => {
                head.setFrame(state[key].icon);
                head.setScale(state[key].face, 1);
                if (state.say) {
                    state.say = "";
                    if (state[key].face === -1) {
                        sayUI.x = sayUI.x - sayUI.width - 10;
                    }
                    sayUI.setVisible(true);
                    this.time.delayedCall(2000, sayUI.setVisible, [false], sayUI);
                }
            });
        });
        // this.players[0].updateInfo(playerInfo.uid, playerInfo.username);
    }

    createPoker() {
        let pokers = [];
        const cx = this.game.config.width * 0.5, cy = this.game.config.height * 0.4;
        // Phaser.Sprite.call(world.width / 2, game.world.height * 0.4, 'poker', frame);
        for (let i = 1; i <= 54; i++) {
            // let poker = this.add.sprite(cx, cy, 'poker', 54);
            let poker = new Poker(this, cx, cy, 'poker', 54);
            this.add.existing(poker);
            pokers.push(poker);
        }
        subscribe('pokers', state => {
            for (let i = 1; i <= 54; i++) {
                pokers[i - 1].setFrame(state.pokers[i]);
            }
        });

        this.dealPoker([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]);
    }

    dealPoker(pokers) {
        store.dispatch({
            'type': SER_DEAL_POKER,
            'pokers': pokers
        });
        // for (let i = 0; i < 17; i++) {
        //     this.players[2].pokerInHand.push(54);
        //     this.players[1].pokerInHand.push(54);
        //     this.players[0].pokerInHand.push(pokers.pop());
        // }

        // this.players[0].dealPoker();
        // this.players[1].dealPoker();
        // this.players[2].dealPoker();
        // this.time.delayedCall(1000, function() {
        //    this.send_message([Protocol.CLI_CHEAT, this.players[1].uid]);
        //    this.send_message([Protocol.CLI_CHEAT, this.players[2].uid]);
        // }, [], this);
    }


    createButton() {
        let group = this.add.group();

        let sy = this.world.height * 0.6;
        let pass = this.add.sprite(0, sy, "ui", "pass.png");
        pass.anchor.set(0.5, 0);
        pass.on("pointerup", () => this.onPass());
        group.add(pass);

        let hint = this.add.sprite(0, sy, "ui", "hint.png");
        hint.anchor.set(0.5, 0);
        hint.on("pointerup", () => this.onHint());
        group.add(hint);

        let shot = this.add.sprite(0, sy, "ui", "shot.png");
        shot.anchor.set(0.5, 0);
        shot.on("pointerup", () => this.onShot());
        group.add(shot);

        // group.forEach(child => child.kill());
    }

    onopen() {
        // const tableId = store.getState().tableId;
        // Socket.send([Protocol.CLI_JOIN_TABLE, tableId]);
        // if (this.tableId === 1) {
        // 	Socket.send([Protocol.CLI_JOIN_TABLE, -1]);
        // } else {
        // 	this.createTableLayer(packet[1]);
        // }
    }

    onerror() {
        console.log('socket connect onerror');
    }

    send_message(request) {
        Socket.send(request);
    }

    onmessage(packet) {
        let opCode = packet[0];
        switch (opCode) {
            case Protocol.SER_LIST_TABLE:
                this.createTableLayer(packet[1]);
                break;
            case Protocol.SER_CREATE_TABLE:
                // const tableId = packet[1];
                // this.titleBar.text = '房间:' + this.tableId;
                // store.dispatch({type: SER_CREATE_TABLE, });
                break;
            case Protocol.SER_JOIN_TABLE:
                const tid = packet[1];
                store.dispatch({type: SER_CREATE_TABLE, tid});

                let playerIds = packet[2];
                for (let i = 0; i < playerIds.length; i++) {
                    if (playerIds[i][0] === this.players[0].uid) {
                        let info_1 = playerIds[(i + 1) % 3];
                        let info_2 = playerIds[(i + 2) % 3];
                        this.players[1].updateInfo(info_1[0], info_1[1]);
                        this.players[2].updateInfo(info_2[0], info_2[1]);
                        break;
                    }
                }
                break;
            case Protocol.SER_DEAL_POKER:
                let pokers = packet[2];
                this.dealPoker(pokers);
                this.whoseTurn = this.uidToSeat(packet[1]);
                this.startCallScore(0);
                break;
            case Protocol.SER_CALL_SCORE:
                let playerId = packet[1];
                let score = packet[2];
                let callend = packet[3];
                this.whoseTurn = this.uidToSeat(playerId);

                const words = ['不叫', "一分", "两分", "三分"];
                store.dispatch({'type': SER_CHAT, seat: this.whoseTurn, say: words[score]});
                // this.players[this.whoseTurn].say(hanzi[score]);
                if (!callend) {
                    this.whoseTurn = (this.whoseTurn + 1) % 3;
                    this.startCallScore(score);
                }
                break;
            case Protocol.SER_HOLE_POKER:
                this.whoseTurn = this.uidToSeat(packet[1]);
                this.tablePoker[0] = packet[2][0];
                this.tablePoker[1] = packet[2][1];
                this.tablePoker[2] = packet[2][2];
                this.players[this.whoseTurn].setLandlord();
                this.showLastThreePoker();
                break;
            case Protocol.SER_SHOT_POKER:
                this.handleShotPoker(packet);
                break;
            case Protocol.SER_GAME_OVER:
                let winner = packet[1];
                let coin = packet[2];

                let loserASeat = this.uidToSeat(packet[3][0]);
                this.players[loserASeat].replacePoker(packet[3], 1);
                this.players[loserASeat].reDealPoker();

                let loserBSeat = this.uidToSeat(packet[4][0]);
                this.players[loserBSeat].replacePoker(packet[4], 1);
                this.players[loserBSeat].reDealPoker();
//                 this.players[loserBSeat].removeAllPoker();
//               this.players[loserASeat].pokerInHand = [];

                this.whoseTurn = this.uidToSeat(winner);

            function gameOver() {
                alert(this.players[this.whoseTurn].isLandlord ? "地主赢" : "农民赢");
                Socket.send([Protocol.CLI_RESTART]);
                this.cleanWorld();
            }

                this.game.time.events.add(3000, gameOver, this);
                break;
            case Protocol.SER_CHEAT:
                let seat = this.uidToSeat(packet[1]);
                this.players[seat].replacePoker(packet[2], 0);
                this.players[seat].reDealPoker();
                break;
            case Protocol.SER_RESTART:
                this.restart();
            default:
                console.log("UNKNOWN PACKET:", packet)
        }
    }

    cleanWorld() {
        for (let i = 0; i < 3; i++) {
            this.players[i].cleanPokers();
            this.players[i].uiLeftPoker.kill();
            this.players[i].uiHead.frameName = 'icon_farmer.png';
        }

        for (let i = 0; i < this.tablePoker.length; i++) {
            let p = this.tablePokerPic[this.tablePoker[i]];
            p.destroy();
        }
    }

    restart() {
        this.players = [];
        this.tablePokerPic = {};
        this.lastShotPlayer = null;
        this.whoseTurn = 0;
        // this.player_id = [1, 11, 12];
        // for (let i = 0; i < 3; i++) {
            //this.players[i].uiHead.kill();
            // this.players[i].updateInfo(player_id[i], ' ');
        // }

        // this.send_message([Protocol.CLI_DEAL_POKEER, -1]);
       // Socket.send([Protocol.CLI_JOIN_TABLE, this.tableId]);
    }

    uidToSeat(uid) {
        for (let i = 0; i < 3; i++) {
            if (uid === this.players[i].uid)
                return i;
        }
        console.log('ERROR uidToSeat:' + uid);
        return -1;
    }

    showLastThreePoker() {
        for (let i = 0; i < 3; i++) {
            let pokerId = this.tablePoker[i];
            let p = this.tablePoker[i + 3];
            p.id = pokerId;
            p.frame = pokerId;
            this.add.tween(p).to({x: this.game.config.width / 2 + (i - 1) * 60}, 600, Phaser.Easing.Default, true);
        }
        this.game.time.events.add(1500, this.dealLastThreePoker, this);
    }

    dealLastThreePoker() {
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
                let tween = this.add.tween(p).to({y: this.game.config.height - PH * 0.8}, 400, Phaser.Easing.Default, true);

                function adjust(p) {
                    this.add.tween(p).to({y: this.game.config.height - PH / 2}, 400, Phaser.Easing.Default, true, 400);
                };
                tween.onComplete.add(adjust, this, p);
            }
        } else {
            let first = turnPlayer.findAPoker(54);
            for (let i = 0; i < 3; i++) {
                let p = this.tablePoker[i + 3];
                p.frame = 54;
                p.frame = 54;
                this.add.tween(p).to({x: first.x, y: first.y}, 200, Phaser.Easing.Default, true);
            }
        }

        this.tablePoker = [];
        this.lastShotPlayer = turnPlayer;
        if (this.whoseTurn === 0) {
            this.startPlay();
        }
    }

    handleShotPoker(packet) {
        // this.whoseTurn = this.uidToSeat(packet[1]);
        // let turnPlayer = this.players[this.whoseTurn];
        // let pokers = packet[2];
        // if (pokers.length === 0) {
        //     this.players[this.whoseTurn].say("不出");
        // } else {
        //     let pokersPic = {};
        //     pokers.sort(Poker.comparePoker);
        //     let count = pokers.length;
        //     let gap = Math.min((this.game.config.width - PW * 2) / count, PW * 0.36);
        //     for (let i = 0; i < count; i++) {
        //         let p = turnPlayer.findAPoker(pokers[i]);
        //         p.id = pokers[i];
        //         p.frame = pokers[i];
        //         p.bringToTop();
        //         this.add.tween(p).to({
        //             x: this.game.config.width / 2 + (i - count / 2) * gap,
        //             y: this.game.config.height * 0.4
        //         }, 500, Phaser.Easing.Default, true);
        //
        //         turnPlayer.removeAPoker(pokers[i]);
        //         pokersPic[p.id] = p;
        //     }
        //
        //     for (let i = 0; i < this.tablePoker.length; i++) {
        //         let p = this.tablePokerPic[this.tablePoker[i]];
        //         p.destroy();
        //     }
        //     this.tablePoker = pokers;
        //     this.tablePokerPic = pokersPic;
        //     this.lastShotPlayer = turnPlayer;
        //     turnPlayer.arrangePoker();
        // }
        // if (turnPlayer.pokerInHand.length > 0) {
        //     this.whoseTurn = (this.whoseTurn + 1) % 3;
        //     if (this.whoseTurn === 0) {
        //         this.game.time.events.add(1000, this.startPlay, this);
        //     }
        // }
    }

    startCallScore(minscore) {
        // if (this.whoseTurn === 0) {
        //     let step = this.game.config.width / 6;
        //     let ss = [1.5, 1, 0.5, 0];
        //     let sx = this.game.config.width / 2 - step * ss[minscore];
        //     let sy = this.game.config.height * 0.6;
        //     let group = this.add.group();
        //     let pass = this.add.sprite(sx, sy, "ui", "score_0.png");
        //     pass.anchor.set(0.5, 0);
        //     pass.score = 0;
        //     pass.on('pointerup', () => {
        //         this.send_message([Protocol.CLI_CALL_SCORE, btn.score]);
        //         btn.parent.destroy();
        //         let audio = this.add.audio('f_score_' + btn.score);
        //         audio.play();
        //     });
        //     group.add(pass);
        //     sx += step;
        //
        //     for (let i = minscore + 1; i <= 3; i++) {
        //         let tn = "score_" + i + ".png";
        //         let call = this.add.sprite(sx, sy, "ui", tn);
        //         call.on('pointerup', (pointer, btn) => {
        //             this.send_message([Protocol.CLI_CALL_SCORE, btn.score]);
        //             btn.parent.destroy();
        //             // this.sound.playAudioSprite("f_score_" + btn.score);
        //         });
        //         call.anchor.set(0.5, 0);
        //         call.score = i;
        //         group.add(call);
        //         sx += step;
        //     }
        // } else {
        //     // TODO show clock on player
        // }
    }

    startPlay() {
        if (this.isLastShotPlayer()) {
            this.players[0].playPoker([]);
        } else {
            this.players[0].playPoker(this.tablePoker);
        }
    }

    finishPlay(pokers) {
        this.send_message([Protocol.CLI_SHOT_POKER, pokers]);
    }

    isLastShotPlayer() {
        return this.players[this.whoseTurn] === this.lastShotPlayer;
    }

    createTableLayer(tables) {
        tables.push([-1, 0]);

        let group = this.add.group();
        this.game.config.bringToTop(group);
        let gc = this.game.make.graphics(0, 0);
        gc.beginFill(0x00000080);
        gc.endFill();
        group.add(gc);
        let style = {font: "22px Arial", fill: "#fff", align: "center"};

        for (let i = 0; i < tables.length; i++) {
            let sx = this.game.config.width * (i % 6 + 1) / (6 + 1);
            let sy = this.game.config.height * (Math.floor(i / 6) + 1) / (4 + 1);

            let table = this.game.make.button(sx, sy, 'btn', this.onJoin, this, 'room.png', 'room.png', 'room.png');
            table.anchor.set(0.5, 1);
            table.tableId = tables[i][0];
            group.add(table);

            let text = this.game.make.text(sx, sy, '房间:' + tables[i][0] + '人数:' + tables[i][1], style);
            text.anchor.set(0.5, 0);
            group.add(text);

            if (i === tables.length - 1) {
                text.text = '新建房间';
            }
        }
    }

    quitGame() {
        this.state.start('MainMenu');
    }

    onJoin(btn) {
        if (btn.tableId === -1) {
            this.send_message([Protocol.CLI_CREATE_TABLE]);
        } else {
            this.send_message([Protocol.CLI_JOIN_TABLE, btn.tableId]);
        }
        btn.parent.destroy();
    }
}

export default GameScene;






