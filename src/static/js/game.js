
PG.Game = function(game) {

    this.players = [];

    this.tableId = 0;
    this.uiShotBtn = null;
    
    this.tablePoker = [];
    this.tablePokerPic = {};
    
    this.lastShotPlayer = null;

    this.whoseTurn = 0;
};

PG.Game.prototype = {

	create: function () {
        this.stage.backgroundColor = '#182d3b';

        this.players.push(PG.createPlay(0, this));
        this.players.push(PG.createPlay(1, this));
        this.players.push(PG.createPlay(2, this));

        PG.Socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));
	},
	
	onopen: function() {
	    console.log('onopen');
	    this.send_message([11]);
	},
	
	send_message: function(request) {
        PG.Socket.send(request);
	},
	
	onmessage: function(packet) {
	    var opcode = packet[0];
	    switch(opcode) {
	        case PG.Protocol.RSP_LOGIN:
                this.players[0].updateInfo(packet[1], packet[2]);
                this.send_message([PG.Protocol.REQ_JOIN_TABLE, -1]);
                break;
	        case PG.Protocol.RSP_JOIN_TABLE:
                this.tableId = packet[1];
                var playerIds = packet[2];
                for (var i = 0; i < playerIds.length; i++) {
                    if (playerIds[i][0] == this.players[0].uid) {
                        var info_1 = playerIds[(i+1)%3];
                        var info_2 = playerIds[(i+2)%3];
                        this.players[1].updateInfo(info_1[0], info_1[1]);
                        this.players[2].updateInfo(info_2[0], info_2[1]);
                        break;
                    }
                }
                break;
            case PG.Protocol.RSP_DEAL_POKER:
                var playerId = packet[1];
                var pokers = packet[2];
                this.dealPoker(pokers);
                this.whoseTurn = this.uidToSeat(playerId);
                this.startCallScore(0);
                break;
            case PG.Protocol.RSP_CALL_SCORE:
                var playerId = packet[1];
                var score = packet[2];
                var callend = packet[3];
                this.whoseTurn = this.uidToSeat(playerId);

                var hanzi = ['不叫', "一分", "两分", "三分"];
                this.players[this.whoseTurn].say(hanzi[score]);
                if (!callend) {
                    this.whoseTurn = (this.whoseTurn + 1) % 3;
                    this.startCallScore(score);
                }
                break;
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
                var playerId = packet[1];
                var coin = packet[2];
                this.whoseTurn = this.uidToSeat(playerId);
                function gameOver() {
                    alert(this.players[this.whoseTurn].isLandlord ? "地主赢" : "农民赢");
                }
                this.game.time.events.add(1000, gameOver, this);
                break;
	    }
	},
	
	onerror: function() {
	    console.log('connect server fail');
	},

	update: function () {
        
	},

	quitGame: function () {
		this.state.start('MainMenu');
	},
	
	uidToSeat: function (uid) {
	    for (var i = 0; i < 3; i++) {
	        if (uid == this.players[i].uid)
	            return i;
	    }
	    console.log('error uid:' + uid);
	    return -1;
	},
    
    dealPoker: function(pokers) {

        for (var i = 0; i < 3; i++) {
            var p = new PG.Poker(this, 54, 54);
            this.world.add(p);
            this.tablePoker[i] = p.id;
            this.tablePoker[i + 3] = p;
        }

        for (var i = 0; i < 17; i++) {
            this.players[2].pokerInHand.push(54);
            this.players[1].pokerInHand.push(54);
            this.players[0].pokerInHand.push(pokers.pop());
        }

        this.players[0].sortPoker();
        
        //to(properties, duration, ease, autoStart, delay, repeat, yoyo)
        var headX = [
            0,
            this.world.width - PG.PW/2,
            PG.PW/2
        ];

        var headY = [
            this.world.height - PG.PH/2,
            this.players[1].uiHead.y + PG.PH/2 + 10,
            this.players[1].uiHead.y + PG.PH/2 + 10
        ];

        for (var i = 0; i < 17; i++) {
            for (var turn = 0; turn < 3; turn++) {
                var pid = this.players[turn].pokerInHand[i];
                var p = new PG.Poker(this, pid, pid);
                this.world.add(p);
                this.players[turn].pushAPoker(p);

                if (turn == 0) {
                    headX[0] = this.world.width/2 + PG.PW * 0.44 * (i - 8.5);
                }
                this.add.tween(p).to({ x: headX[turn], y: headY[turn] }, 500, Phaser.Easing.Default, true, (turn == 0 ? 0 : 25) + i * 50);
            }
        }
    },
     
    showLastThreePoker: function() {
        for (var i = 0; i < 3; i++) {
            var pokerId = this.tablePoker[i];
            var p = this.tablePoker[i + 3];
            p.id = pokerId;
            p.frame = pokerId;
            this.add.tween(p).to({ x: this.world.width/2 + (i - 1) * 60}, 600, Phaser.Easing.Default, true);
        }
        
         this.game.time.events.add(1500, this.dealLastThreePoker, this);
    },
    
    arrangePoker: function() {
        this.players[0].sortPoker();
        var count = this.players[0].pokerInHand.length;
        var gap = Math.min(this.world.width / count, PG.PW * 0.36);
        for (var i = 0; i < count; i++) {
            var pid = this.players[0].pokerInHand[i];
            var p = this.players[0].findAPoker(pid);
            p.bringToTop();
            this.add.tween(p).to({ x: this.world.width/2 + (i - count/2) * gap}, 600, Phaser.Easing.Default, true);
        }
    },
    
    dealLastThreePoker: function() {
	    var turnPlayer = this.players[this.whoseTurn];

        for (var i = 0; i < 3; i++) {
            var pid = this.tablePoker[i];
            var poker = this.tablePoker[i + 3];
            turnPlayer.pokerInHand.push(pid);
            turnPlayer.pushAPoker(poker);
        }
        
        if (this.whoseTurn == 0) {
            this.arrangePoker();
            for (var i = 0; i < 3; i++) {
                var p = this.tablePoker[i + 3];
                var tween = this.add.tween(p).to({y: this.world.height - PG.PH * 0.8 }, 400, Phaser.Easing.Default, true);
                function adjust(p) {
                    this.add.tween(p).to({y: this.world.height - PG.PH /2}, 400, Phaser.Easing.Default, true, 400);
                };
                tween.onComplete.add(adjust, this, p);
            }
        } else {
            var first = turnPlayer.findAPoker(54);
            for (var i = 0; i < 3; i++) {
                var p = this.tablePoker[i + 3];
                p.frame = 54;
                this.add.tween(p).to({ x: first.x, y: first.y}, 200, Phaser.Easing.Default, true);
            }
        }

        this.tablePoker = [];
        this.lastShotPlayer = turnPlayer;
        if (this.whoseTurn == 0) {
            this.startPlay();
        }
    },

    handleShotPoker: function(packet) {
        var playerId = packet[1];
        var pokers = packet[2];
        this.whoseTurn = this.uidToSeat(playerId);
        var turnPlayer = this.players[this.whoseTurn];
        if (pokers.length == 0) {
            this.players[this.whoseTurn].say("不出");
        } else {
            var pokersPic = {};
            pokers.sort(PG.Poker.comparePoker);
            var count= pokers.length;
            var gap = Math.min((this.world.width - PG.PW * 2) / count, PG.PW * 0.36);
            for (var i = 0; i < count; i++) {
                var p = turnPlayer.findAPoker(pokers[i]);
                p.id = pokers[i];
                p.frame = pokers[i];
                p.bringToTop();
                this.add.tween(p).to({ x: this.world.width/2 + (i - count/2) * gap, y: this.world.height * 0.4}, 500, Phaser.Easing.Default, true);

                turnPlayer.removeAPoker(pokers[i]);
                pokersPic[p.id] = p;
            }
        
            for (var i = 0; i < this.tablePoker.length; i++) {
                var p = this.tablePokerPic[this.tablePoker[i]];
                // p.kill();
                p.destroy();
            }
            this.tablePoker = pokers;
            this.tablePokerPic = pokersPic;
            this.lastShotPlayer = turnPlayer;
            if (this.whoseTurn == 0) {
                this.arrangePoker();
            }
            console.log("shot poker:", this.tablePoker);
        }
        if (!this.isGameOver()) {
            this.whoseTurn = (this.whoseTurn + 1) % 3;
            if (this.whoseTurn == 0) {
                this.game.time.events.add(1000, this.startPlay, this);
            }
        }
    },

    isGameOver: function() {
	    for (var i = 0; i < 3; i++) {
	        if (this.players[i].pokerInHand.length === 0) {
	            return true;
            }
        }
        return false;
    },

    startCallScore: function(minscore) {

        function btnTouch(btn) {
            this.send_message([PG.Protocol.REQ_CALL_SCORE, btn.score]);
            //FIXME: delay to next frame
            btn.parent.destroy();
        };

        if (this.whoseTurn == 0) {
            var step = this.world.width/6;
            var ss = [1.5, 1, 0.5, 0];
            var sx = this.world.width/2 - step * ss[minscore];
            var sy = this.world.height * 0.6;
            var group = this.add.group();
            var pass = this.add.button(sx, sy, "btn", btnTouch, this, 'score_0.png', 'score_0.png', 'score_0.png');
            pass.anchor.set(0.5, 0);
            pass.score = 0;
            group.add(pass);
            sx += step;

            for (var i = minscore + 1; i <= 3; i++) {
                var tn = 'score_' + i + '.png';
                var call = this.add.button(sx, sy, "btn", btnTouch, this, tn, tn, tn);
                call.anchor.set(0.5, 0);
                call.score = i;
                group.add(call);
                sx += step;
            }
        } else {
            // TODO show clock on player
        }
        
    },

    startPlay: function() {
        if (this.isLastShotPlayer()) {
            this.players[0].playPoker([]);
        } else {
            this.players[0].playPoker(this.tablePoker);
        }
    },

    finishPlay: function(pokers) {
        console.log('finishPlay', pokers);
        this.send_message([PG.Protocol.REQ_SHOT_POKER, pokers]);
    },

    isLastShotPlayer: function() {
        return this.players[this.whoseTurn] == this.lastShotPlayer;
    },

    shufflePoker: function() {
        var pokers = [];
        for (var i = 0; i < 54; i++) {
            pokers.push(i);
        }
        
        var currentIndex = pokers.length, temporaryValue, randomIndex ;
        while (0 != currentIndex) {
            randomIndex = Math.floor(Math.random() * currentIndex);
            currentIndex -= 1;
            
            temporaryValue = pokers[currentIndex];
            pokers[currentIndex] = pokers[randomIndex];
            pokers[randomIndex] = temporaryValue;
        }
        return pokers;
    }
    
};






