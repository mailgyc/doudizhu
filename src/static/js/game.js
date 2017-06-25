
PG.Game = function(game) {

    this.players = [];
    this.players.push(new PG.Player(0, this));
    
    this.tableid = 0;
    
    this.callscore = 0;

    this.pokerDB = {};
    this.tablePoker = [];
    
    this.lastShotPlayer = null;

    this.whoseTurn = 0;
    this.hintPoker = [];

    this.isDraging = false;
};

PG.Game.prototype = {

	create: function () {
        this.stage.backgroundColor = '#182d3b';

        this.players.push(new PG.NetPlayer(1, this));
        this.players.push(new PG.NetPlayer(2, this));

        var coords = [
            PG.PW/2, this.world.height - PG.PH - 10, 0.5, 1.0,
            this.world.width - PG.PW/2, 0, 0.5, 0,
            PG.PW/2, 0,                    0.5, 0
            ];
        for (var i = 0; i < this.players.length; i++) {
            this.players[i].head = this.add.sprite(coords[i*4], coords[i*4+1], 'btn', 'farmer.png');
            this.players[i].head.anchor.set(coords[i*4+2], coords[i*4+3]);
            
            this.players[i].leftPoker = this.add.text(coords[i*4], coords[i*4+1] + PG.PH + 100, '17', {});
        }
        
        this.players[1].head.scale.set(-1, 1);
        
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
                this.players[0].pid = packet[1];
                this.players[0].name = packet[2];
                this.send_message([PG.Protocol.REQ_JOIN_TABLE, -1]);
                break;
	        case PG.Protocol.RSP_JOIN_TABLE:
                this.tableid = packet[1];
                var playerIds = packet[2];
                for (var i = 0; i < playerIds.length; i++) {
                    if (playerIds[i] == this.players[0].pid) {
                        this.players[1].pid = playerIds[(i+1)%3]; 
                        this.players[2].pid = playerIds[(i+2)%3]; 
                        break;
                    }
                }
                break;
            case PG.Protocol.RSP_DEAL_POKER:
                var playerId = packet[1];
                var pokers = packet[2];
                if (pokers.length < 54) {
                    for (var i = 0; i < 17; i++) {
                        pokers.push(55)
                    }
                    for (var i = 0; i < 17; i++) {
                        pokers.push(56)
                    }
                    for (var i = 0; i < 3; i++) {
                        pokers.push(54)
                    }
                }
                
                this.dealPoker(pokers);
                this.whoseTurn = this.pidToSeat(playerId);
                this.startCallScore(this.callscore);
                break;
            case PG.Protocol.RSP_CALL_SCORE:
                var playerId = packet[1];
                var score = packet[2];
                var callend = packet[3];
                this.whoseTurn = this.pidToSeat(playerId);

                var hanzi = ['不叫', "一分", "两分", "三分"];
                this.playerSay(hanzi[score]);
                this.whoseTurn = (this.whoseTurn + 1) % 3;
                if (callend) {
                    this.startPlay();
                } else {
                    this.startCallScore(this.callscore);
                }
                break
            case PG.Protocol.RSP_SHOT_POKER:
                this.tablePoker[0] = packet[1][0];
                this.tablePoker[1] = packet[1][1];
                this.tablePoker[2] = packet[1][2];
                this.players[this.whoseTurn].isLandlord = true;
                this.players[this.whoseTurn].head.frame = 2;
                this.showLastThreePoker();
                break;
            case PG.Protocol.RSP_SHOT_POKER:
                if (this.lastShotPlayer == null) {
                    this.game.time.events.add(2000, this.handleShotPoker, this, packet);
                } else {
                    this.handleShotPoker(packet);
                }
                break;
            case PG.Protocol.RSP_GAME_OVER:
                var playerId = packet[1];
                var coin = packet[2];
                this.whoseTurn = this.pidToSeat(playerId);
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
	
	pidToSeat: function (pid) {
	    for (var i = 0; i < 3; i++) {
	        if (pid == this.players[i].pid)
	            return i;
	    }
	    console.log('error pid:' + pid);
	    return -1;
	},
    
    dealPoker: function(pokers) {
        for (var i = 0; i < 3; i++) {
            var p = new PG.Poker(this, pokers.pop(), 54);
            this.world.add(p);
            this.tablePoker[i] = p.id;
            this.tablePoker[i + 3] = p;
        }

        for (var i = 0; i < 17; i++) {
            this.players[2].pokerInHand.push(pokers.pop());
        }
        for (var i = 0; i < 17; i++) {
            this.players[1].pokerInHand.push(pokers.pop());
        }
        for (var i = 0; i < 17; i++) {
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
            this.players[1].head.y + this.players[1].head.height + PG.PH/2 + 10,
            this.players[1].head.y + this.players[1].head.height + PG.PH/2 + 10
        ];

        var copy = this.whoseTurn;
        var gap = Math.min(this.world.width/17, PG.PW * 0.36);
        for (var i = 0; i < 17; i++) {
            for (var turn = 0; turn < 3; turn++) {
                var pid = this.players[turn].pokerInHand[i];
                var p = new PG.Poker(this, pid, turn == 0 ? pid : 54);
                this.world.add(p);

                if (turn == 0) {
                    headX[0] = this.world.width/2 + gap * (i - 8.5);
                }
                this.add.tween(p).to({ x: headX[turn], y: headY[turn] }, 500, Phaser.Easing.Default, true, (turn == 0 ? 0 : 25) + i * 50);
                
                this.whoseTurn = turn;
                this.pushInDB(p.id, p);
            }
        }
        this.whoseTurn = copy;
    },
     
    finishCallScore: function(score) {
        this.send_message([PG.Protocol.REQ_CALL_SCORE, score]);
    },
    
    showLastThreePoker: function() {
        for (var i = 0; i < 3; i++) {
            var pokerid = this.tablePoker[i];
            var p = this.tablePoker[i + 3];
            p.id = pokerid;
            p.frame = pokerid;
            this.add.tween(p).to({ x: this.world.width/2 + (i - 1) * 60}, 600, Phaser.Easing.Default, true);
        }
        
        this.time.events.add(1500, this.dealLastThreePoker, this);
    },
    
    arrangePoker: function() {
        this.players[this.whoseTurn].sortPoker();
        
        var count = this.players[0].pokerInHand.length;
        var gap = Math.min(this.world.width / count, PG.PW * 0.36);
        for (var i = 0; i < count; i++) { 
            var pokerid = this.players[0].pokerInHand[i];
            var p = this.findInDB(pokerid);
            p.bringToTop();
            this.add.tween(p).to({ x: this.world.width/2 + (i - count/2) * gap}, 600, Phaser.Easing.Default, true);
        }
    },
    
    dealLastThreePoker: function() {
        for (var i = 0; i < 3; i++) {
            var pid = this.tablePoker[i];
            var poker = this.tablePoker[i + 3];
            this.players[this.whoseTurn].pokerInHand.push(pid);
            this.pushInDB(pid, poker);
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
            var first = this.findInDB(this.players[this.whoseTurn].pokerInHand[0]);
            for (var i = 0; i < 3; i++) {
                var p = this.tablePoker[i + 3];
                p.frame = 54;
                this.add.tween(p).to({ x: first.x, y: first.y}, 200, Phaser.Easing.Default, true);
            }
            this.players[this.whoseTurn].sortPoker();
            this.players[this.whoseTurn].leftPoker.text = "20";
        }
        
        var length = this.players[0].pokerInHand.length;
        for (var i = 0; i < length;  i++) {
            var pokerid = this.players[0].pokerInHand[i];
            var p = this.findInDB(pokerid);
            p.events.onInputDown.add(this.onInputDown, this);
            p.events.onInputUp.add(this.onInputUp, this);
            p.events.onInputOver.add(this.onInputOver, this);
        }
        
        this.tablePoker = [];
        this.lastShotPlayer = this.players[this.whoseTurn];
        this.startPlay();
    },

    handleShotPoker: function(packet) {
        var playerId = packet[1];
        var pokers = packet[2];
        var shotend = packet[3];
        this.whoseTurn = this.pidToSeat(playerId);
        if (pokers.length == 0) {
            this.playerSay("不出");
        } else {
            
            pokers.sort(PG.Poker.comparePoker);
            var count= pokers.length;
            var gap = Math.min((this.world.width - PG.PW * 2) / count, PG.PW * 0.36);
            for (var i = 0; i < count; i++) {
                var p = this.removeInDB(pokers[i]);
                p.id = pokers[i];
                p.frame = pokers[i];
                p.bringToTop();
                this.add.tween(p).to({ x: this.world.width/2 + (i - count/2) * gap, y: this.world.height * 0.4}, 500, Phaser.Easing.Default, true);
                this.pushInDB(p.id, p);
                
                this.players[this.whoseTurn].removeAPoker(pokers[i]);
            }
        
            if (this.players[this.whoseTurn].leftPoker) {
                this.players[this.whoseTurn].leftPoker.text = this.players[this.whoseTurn].pokerInHand.length + "";
            }
            
            for (var i = 0; i < this.tablePoker.length; i++) {
                var p = this.removeInDB(this.tablePoker[i]);
                p.kill();
            }
            this.tablePoker = pokers;
            this.lastShotPlayer = this.players[this.whoseTurn];
        }
            
        this.arrangePoker();
        if (!shotend) {
            this.whoseTurn = (this.whoseTurn + 1) % 3;
            this.game.time.events.add(1000, this.startPlay, this);
        }
    },

    onInputDown: function(poker, pointer) {
        this.isDraging = true;
        this.selectPoker(poker, pointer);
    },
    
    onInputUp: function(poker, pointer) {
        this.isDraging = false;
        //this.selectPoker(poker, pointer);
    },
    
    onInputOver: function(poker, pointer) {
        if (this.isDraging) {
            this.selectPoker(poker, pointer);
        }     
    },
    
    startPlay: function() {
        
        if (this.players[this.whoseTurn] == this.lastShotPlayer) {
            this.players[this.whoseTurn].playPoker([]);
        } else {
            this.players[this.whoseTurn].playPoker(this.tablePoker);
        }
        
    },
    
    finishPlay: function(pokers) {
        this.send_message([PG.Protocol.REQ_GAME_OVER, pokers]);
    },
    
    // function about ui
    playerSay: function(str) {
        var head = this.players[this.whoseTurn].head;
            
        var style = { font: "22px Arial", fill: "#ff0000", align: "center" };
		var text = this.add.text(head.x + head.width/2, head.y + head.height * (head.anchor.y == 0 ? 0.5 : -0.5), str, style);
		if (head.scale.x == -1) {
		    text.x = text.x - text.width;
		}
        this.time.events.add(2000, text.destroy, text); 
    },
    
    startCallScore: function(minscore) {

        function btnTouch(btn) {
            btn.parent.destroy(true);
            this.finishCallScore(btn.score)
        };

        if (this.whoseTurn == 0) {
            var step = this.world.width/6;
            var sx = this.world.width/2 - (2 - minscore) * step, sy = this.world.height * 0.6;
            var group = this.add.group();
            var pass = this.add.button(sx, sy, "btn", btnTouch, this, 'score_0.png', 'score_0.png', 'score_0.png');
            pass.scale.set(0.8);
            pass.score = 0;
            group.add(pass);
            sx += step;

            for (var i = minscore + 1; i <= 3; i++) {
                var tn = 'score_' + i + '.png';
                var call = this.add.button(sx, sy, "btn", btnTouch, this, tn, tn, tn);
                call.scale.set(0.8);
                call.score = i;
                group.add(call);
                sx += step;
            }
        } else {
            // TODO show clock on player
        }
        
    },
    
    selectPoker: function(poker, pointer) {

        var index = this.hintPoker.indexOf(poker.id);
        if ( index == -1) {
            poker.y = this.world.height - PG.PH * 0.8;
            this.hintPoker.push(poker.id);
        } else {
            poker.y = this.world.height - PG.PH * 0.5;
            this.hintPoker.splice(index, 1);
        }

    },
    
    playerPlayPoker: function(lastTurnPoker) {
        function pass(btn) {
            this.finishPlay([]);
            for (var i = 0; i < this.hintPoker.length; i++) {
                var p = this.findInDB(this.hintPoker[i]);
                p.y = this.world.height - PG.PH/2;
            }
            this.hintPoker = [];
            btn.parent.destroy(true);
        }
        function hint(btn) {
            if (this.hintPoker.length == 0) {
                this.hintPoker = lastTurnPoker;
            } else {
                for (var i = 0; i < this.hintPoker.length; i++) {
                    var p = this.findInDB(this.hintPoker[i]);
                    p.y = this.world.height - PG.PH/2;
                }
            }
            var bigger = this.players[this.whoseTurn].hint(this.hintPoker); 
            if (bigger.length == 0) {
                if (this.hintPoker == lastTurnPoker) {
                    this.playerSay("没有能大过的牌");
                } else{
                    for (var i = 0; i < this.hintPoker.length; i++) {
                        var p = this.findInDB(this.hintPoker[i]);
                        p.y = this.world.height - PG.PH/2;
                    }
                }
            } else {
                for (var i = 0; i < bigger.length; i++) {
                    var p = this.findInDB(bigger[i]);
                    p.y = this.world.height - PG.PH * 0.8;
                }
            }
            this.hintPoker = bigger;
        }
        function shot(btn) {
            if  (this.hintPoker.length == 0) {
                return;
            }
            var code = this.players[0].canPlay((this.players[this.whoseTurn] == this.lastShotPlayer) ? [] : this.tablePoker, this.hintPoker);
            if (code == -1) {
                this.playerSay("出牌不符合规矩");
                return;
            }
            if (code == 0) {
                this.playerSay("出牌必须大于上家的牌");
                return;
            }
            this.finishPlay(this.hintPoker);
            this.hintPoker = [];
            btn.parent.destroy(true);
        }
        var group = this.add.group();
        if (this.players[this.whoseTurn] != this.lastShotPlayer) {
            var pass = this.add.button(this.world.width/2 - 80, this.world.height * 0.6, "btn", pass, this, 'pass.png', 'pass.png', 'pass.png');
            group.add(pass);
        }
        var hint = this.add.button(this.world.width/2, this.world.height * 0.6, "btn", hint, this, 'hint.png', 'hint.png', 'hint.png');
        group.add(hint);
        var pass = this.add.button(this.world.width/2 + 80, this.world.height * 0.6, "btn", shot, this, 'shot.png', 'shot.png', 'shot.png');
        group.add(shot);
        
        
        var length = this.players[0].pokerInHand.length;
        for (var i = 0; i < length; i++) {
            var p = this.findInDB(this.players[0].pokerInHand[i]);
            p.inputEnabled = true;
        }
    },

    pushInDB: function(pid, poker) {
        if (pid < 54) {
            this.pokerDB[pid] = poker;
        } else {
            if (this.pokerDB[this.whoseTurn + 54]) {
                this.pokerDB[this.whoseTurn + 54].push(poker);
            } else {
                this.pokerDB[this.whoseTurn + 54] = [poker];
            }
        }
    },

    findInDB: function(pid) {
        
        if (pid < 54) {
            var poker = this.pokerDB[pid];
            if (poker) {
                return poker;
            }
        }
        // 54 table poker
        // 55 56 player poker
        return this.pokerDB[this.whoseTurn + 54][0];
    },

    removeInDB: function(pid) {
        if (pid < 54) {
            var poker = this.pokerDB[pid];
            if (poker) {
                delete this.pokerDB[pid];
                return poker;
            }
        }
        // 54 table poker
        // 55 56 player poker
        var pokers = this.pokerDB[this.whoseTurn + 54].splice(0, 1);
        return pokers[0];
    },

    shufflePoker: function() {
        var pokers = [];
        for (var i = 0; i < 54; i++) {
            pokers.push(i);
        }
        
        var currentIndex = pokers.length, temporaryValue, randomIndex ;
        while (0 !== currentIndex) {
            randomIndex = Math.floor(Math.random() * currentIndex);
            currentIndex -= 1;
            
            temporaryValue = pokers[currentIndex];
            pokers[currentIndex] = pokers[randomIndex];
            pokers[randomIndex] = temporaryValue;
        }
        return pokers;
    }
    
};






