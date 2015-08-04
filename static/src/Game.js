
PokerGame.Game = function(game) {

    this.players = [];
    this.players.push(new PokerGame.Player(0, this));
    if (PokerGame.gameType == 0) {
        this.players.push(new PokerGame.AIPlayer(1, this));
        this.players.push(new PokerGame.AIPlayer(2, this));
    } else {
        this.players.push(new PokerGame.NetPlayer(1, this));
        this.players.push(new PokerGame.NetPlayer(2, this));
    }
    
    this.pid = 0;
    this.pokerDB = {};
    this.lastThreePoker = [];
    
    this.callscore = 0;
    this.whoseTurn = 0;
    this.lastShotPlayer = null;
    this.lastShotPoker = [];
    this.hintPoker = [];
    this.isDraging = false;
};

PokerGame.Game.prototype = {

	create: function () {
        this.stage.backgroundColor = '#182d3b';
        
        var coords = [
            PokerGame.PW/2, this.world.height - PokerGame.PH - 10, 0.5, 1.0,
            this.world.width - PokerGame.PW/2, 0, 0.5, 0,
            PokerGame.PW/2, 0,                    0.5, 0,
            ];
        for (var i = 0; i < this.players.length; i++) {
            this.players[i].head = this.add.sprite(coords[i*4], coords[i*4+1], 'icon', 1);
            this.players[i].head.anchor.set(coords[i*4+2], coords[i*4+3]);
            
            this.players[i].leftPoker = this.add.text(coords[i*4], coords[i*4+1] + PokerGame.PH + 100, '17', {});
        }
        
        this.players[1].head.scale.set(-1, 1);
        
        if (PokerGame.gameType == 0) {
            this.sendmessage([15]); 
        } else {
            PokerGame.Socket.connect(this.onopen.bind(this), this.onerror.bind(this));
        }
	},
	
	onopen: function() {
	    PokerGame.Socket.onmessage = this.onmessage.bind(this);
	    this.sendmessage([1]);
	},
	
	sendmessage: function(request) {
	    if (PokerGame.gameType == 1) {
	        PokerGame.Socket.send(request);
	    } else {
	        var opcode = request[0];
	        switch(opcode) {
            case 15:     // fast join table
                this.onmessage([16, 1, [this.players[0].pid, this.players[1].pid, this.players[2].pid ]]);
                var turn = this.rnd.integerInRange(0, 2);
                this.onmessage([100, this.players[turn].pid, this.shufflePoker()]);
                if (this.whoseTurn != 0) {
                    this.startCallScore();
                }
                break;
            case 101:    // request call score
                this.callscore = request[1];
                var packet = [102, this.players[this.whoseTurn].pid, this.callscore];
                this.onmessage(packet);

                if (this.callscore == 3 || this.players[(this.whoseTurn+1)%3].hasCalled) {
                    var packet = [104, this.lastThreePoker];
                    this.onmessage(packet);
                } else {
                    this.whoseTurn = (this.whoseTurn + 1) % 3;
                    if (this.whoseTurn != 0) {
                        this.startCallScore();
                    }
                }
                break;
            case 105:   // shot poker
                var pokers = request[1]; 
                this.onmessage([106, pokers]);

                var coin = 100;
                for (var i = 0; i < 3; i++) {
                    if (this.players[i].pokerInHand.length == 0) {
                        this.onmessage([108, this.players[i].pid, coin]);
                        break;
                    }
                }
                break;
	        }
	    }
	},
	
	onmessage: function(packet) {
	    var opcode = packet[0];
	    switch(opcode) {
	        case 2:
                this.players[0].pid = packet[1]; 
                this.sendmessage([15]);
                break;
	        case 16:     // fast join
                this.pid = packet[1];
                var playerIds = packet[2];
                for (var i = 0; i < playerIds.length; i++) {
                    if (playerIds[i] == this.players[0].pid) {
                        this.players[1].pid = playerIds[(i+1)%3]; 
                        this.players[2].pid = playerIds[(i+2)%3]; 
                        break;
                    }
                }
                break;
            case 100:   // deal poker
                var playerId = packet[1];
                var pokers = packet[2];
                for (var i = pokers.length; i < 54; i++) {
                    pokers.push(0); 
                }
                
                this.dealPoker(pokers);
                this.whoseTurn = this.pidToSeat(playerId);
                if (this.whoseTurn == 0) {
                    this.whoseTurn = 0;
                    this.startCallScore();
                }
                break;
            case 102:   // call score
                var playerId = packet[1];
                var score = packet[2];
                
                this.whoseTurn = this.pidToSeat(playerId);
                var hanzi = ['不叫', "一分", "两分", "三分"];
                this.playerSay(hanzi[score]); 
                if ((this.whoseTurn + 1) % 3 == 0) {
                    this.whoseTurn = 0;
                    this.startCallScore();
                }

                break
            case 104: // show last three poker
                this.lastThreePoker = packet[1];
                this.players[this.whoseTurn].isLandlord = true;
                this.players[this.whoseTurn].head.frame = 2;
                this.showLastThreePoker();
                break;
            case 106: // shot poker
                var pokers = packet[1];
                if (pokers.length == 0) {
                    this.playerSay("不出");
                } else {
                    
                    pokers.sort(PokerGame.Poker.comparePoker); 
                    
                    var count= pokers.length;
                    var gap = Math.min((this.world.width - PokerGame.PW * 2) / count, PokerGame.PW * 0.36);
                    for (var i = 0; i < count; i++) {
                        var p = this.pokerDB[pokers[i]];
                        p.frame = pokers[i];
                        p.bringToTop();
                        this.add.tween(p).to({ x: this.world.width/2 + (i - count/2) * gap, y: this.world.height * 0.4}, 500, Phaser.Easing.Default, true);
                        
                        this.players[this.whoseTurn].removeAPoker(pokers[i]);
                    }
                
                    if (this.players[this.whoseTurn].leftPoker) {
                        this.players[this.whoseTurn].leftPoker.text = this.players[this.whoseTurn].pokerInHand.length + "";
                    }
                    
                    this.lastShotPlayer = this.players[this.whoseTurn];
                    for (var i = 0; i < this.lastShotPoker.length; i++) {
                        var pokerid = this.lastShotPoker[i];
                        this.pokerDB[pokerid].kill();
                        delete this.pokerDB[pokerid];
                    }
                    this.lastShotPoker = pokers;
                }
                
                this.whoseTurn = (this.whoseTurn + 1) % 3;
                this.startPlay(); 
                break;
            case 108: // game over
                var playerId = packet[1];
                var coin = packet[2];
                this.whoseTurn = this.pidToSeat(playerId);
                function gameover() {
                    alert(this.players[this.whoseTurn].isLandlord ? "地主赢" : "农民赢");
                }
                this.game.time.events.add(1000, gameover, this);
                break;
	    }
	},
	
	onerror: function() {
	    alert('connect server fail');
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
	    alert('error pid:' + pid);
	    return -1;
	},
    
    dealPoker: function(pokers) {
        for (var i = 0; i < 3; i++) {
            var pid = pokers.pop();
            this.lastThreePoker.push(pid);
            var p = new PokerGame.Poker(this, pid, 54);
            this.world.add(p);
            this.pokerDB[p.id] = p;
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
        
        this.players[0].pokerInHand.sort(PokerGame.Poker.comparePoker);
        this.players[1].pokerInHand.sort(PokerGame.Poker.comparePoker);
        this.players[2].pokerInHand.sort(PokerGame.Poker.comparePoker);
        
        //to(properties, duration, ease, autoStart, delay, repeat, yoyo)
        var gap = Math.min(this.world.width/17, PokerGame.PW * 0.36);
        for (var i = 0; i < 17; i++) {
            var p = new PokerGame.Poker(this, this.players[0].pokerInHand[i], this.players[0].pokerInHand[i]);
            this.world.add(p);
            this.pokerDB[p.id] = p;
            this.add.tween(p).to({ x: this.world.width/2 + gap * (i - 8.5), y: this.world.height - PokerGame.PH/2 }, 500, Phaser.Easing.Default, true, i * 50);
            
            var right = new PokerGame.Poker(this, this.players[1].pokerInHand[i], 54);
            this.world.add(right);
            this.pokerDB[right.id] = right;
            this.add.tween(right).to({ x: this.world.width - PokerGame.PW/2, y: this.players[1].head.y + this.players[1].head.height + PokerGame.PH/2 + 10 },
                                        500, Phaser.Easing.Default, true, 25 + i * 50);
            
            var left = new PokerGame.Poker(this, this.players[2].pokerInHand[i], 54);
            this.world.add(left);
            this.pokerDB[left.id] = left;
            this.add.tween(left).to({ x: PokerGame.PW/2, y: this.players[2].head.y + this.players[2].head.height + PokerGame.PH/2 + 10 }, 
                                        500, Phaser.Easing.Default, true, 25 + i * 50);
        }
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
    },
    
    startCallScore: function () {
        this.players[this.whoseTurn].startCallScore(this.callscore);
    },
    
    finishCallScore: function(score) { 
        this.sendmessage([101, score]);
    },
    
    showLastThreePoker: function() {
        for (var i = 0; i < 3; i++) {
            var pokerid = this.lastThreePoker[i];
            var p = this.pokerDB[pokerid];
            p.frame = pokerid;
            this.add.tween(p).to({ x: this.world.width/2 + (i - 1) * 60}, 600, Phaser.Easing.Default, true);
        }
        
        this.time.events.add(2000, this.dealLastThreePoker, this);
    },
    
    arrangePoker: function() {
        this.players[this.whoseTurn].pokerInHand.sort(PokerGame.Poker.comparePoker);
        
        var count = this.players[0].pokerInHand.length;
        var gap = Math.min(this.world.width / count, PokerGame.PW * 0.36);
        for (var i = 0; i < count; i++) { 
            var pokerid = this.players[0].pokerInHand[i];
            var p = this.pokerDB[pokerid];
            p.bringToTop();
            this.add.tween(p).to({ x: this.world.width/2 + (i - count/2) * gap}, 600, Phaser.Easing.Default, true);
        }
    },
    
    dealLastThreePoker: function() {
        for (var i = 0; i < 3; i++) {
            var pokerid = this.lastThreePoker[i];
            this.players[this.whoseTurn].pokerInHand.push(pokerid);
        }
        
        if (this.whoseTurn == 0) {
            this.arrangePoker();
            for (var i = 0; i < 3; i++) {
                var p = this.pokerDB[this.lastThreePoker.pop()];
                var tween = this.add.tween(p).to({y: this.world.height - PokerGame.PH * 0.8 }, 400, Phaser.Easing.Default, true);
                function adjust(p) {
                    this.add.tween(p).to({y: this.world.height - PokerGame.PH /2}, 400, Phaser.Easing.Default, true, 400);
                };
                tween.onComplete.add(adjust, this, p);
            }
        } else {
            var first = this.pokerDB[this.players[this.whoseTurn].pokerInHand[0]];
            for (var i = 0; i < 3; i++) {
                var p = this.pokerDB[this.lastThreePoker.pop()];
                p.frame = 54;
                this.add.tween(p).to({ x: first.x, y: first.y}, 60, Phaser.Easing.Default, true);
            }
            this.players[this.whoseTurn].pokerInHand.sort(PokerGame.Poker.comparePoker);
            this.players[this.whoseTurn].leftPoker.text = "20";
        }
        
        for (var i = 0; i < this.players[0].pokerInHand.length; i++) {
            var pokerid = this.players[0].pokerInHand[i];
            this.pokerDB[pokerid].events.onInputDown.add(this.onInputDown, this);
            this.pokerDB[pokerid].events.onInputUp.add(this.onInputUp, this);
            this.pokerDB[pokerid].events.onInputOver.add(this.onInputOver, this);
        }
        
        this.lastShotPlayer = this.players[this.whoseTurn];
        this.startPlay();
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
            this.players[this.whoseTurn].playPoker(this.lastShotPoker);
        }
        
    },
    
    finishPlay: function(pokers) {
        this.sendmessage([105, pokers]); 
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
    
    playerCallScore: function(minscore) {
        
        function btnTouch(btn) {
            btn.parent.destroy(true);
            this.finishCallScore(btn.score)
        };
        
        var step = this.world.width/12;
        var sx = this.world.width/2 - (2 - minscore) * step, sy = this.world.height * 0.6;
        var group = this.add.group();
        var pass = new PokerGame.TextButton(this, sx, sy, '不叫', btnTouch, this);
        pass.score = 0;
        group.add(pass);
        sx += step;
    
        var text = ['不叫', "一分", "两分", "三分"];
        for (var i = minscore + 1; i <= 3; i++) {
            var call = new PokerGame.TextButton(this, sx, sy, text[i], btnTouch, this);
            call.score = i;
            group.add(call);
            sx += step;
        }
    },
    
    selectPoker: function(poker, pointer) {
        if (this.hintPoker.indexOf(poker.id) == -1) {
            poker.y = this.world.height - PokerGame.PH * 0.8;
            this.hintPoker.push(poker.id);
        } else {
            poker.y = this.world.height - PokerGame.PH * 0.5;
             for(var i = 0; i < this.hintPoker.length; i++){
               if(this.hintPoker[i] == poker.id){
                    this.hintPoker.splice(i, 1);
                    break;
               }
            }   
        }
    },
    
    playerPlayPoker: function(lastTurnPoker) {
        function pass(btn) {
            this.finishPlay([]);
            for (var i = 0; i < this.hintPoker.length; i++) {
                this.pokerDB[this.hintPoker[i]].y = this.world.height - PokerGame.PH/2;
            }
            this.hintPoker = [];
            btn.parent.destroy(true);
        }
        function hint(btn) {
            if (this.hintPoker.length == 0) {
                this.hintPoker = lastTurnPoker;
            } else {
                for (var i = 0; i < this.hintPoker.length; i++) {
                    this.pokerDB[this.hintPoker[i]].y = this.world.height - PokerGame.PH/2;
                }
            }
            var bigger = this.players[this.whoseTurn].hint(this.hintPoker); 
            if (bigger.length == 0) {
                if (this.hintPoker == lastTurnPoker) {
                    this.playerSay("没有能大过的牌");
                } else{
                    for (var i = 0; i < this.hintPoker.length; i++) {
                        this.pokerDB[this.hintPoker[i]].y = this.world.height - PokerGame.PH/2;
                    }
                }
            } else {
                for (var i = 0; i < bigger.length; i++) {
                    this.pokerDB[bigger[i]].y = this.world.height - PokerGame.PH * 0.8;
                }
            }
            this.hintPoker = bigger;
        }
        function shot(btn) {
            if  (this.hintPoker.length == 0) {
                return;
            }
            var code = this.players[0].canPlay((this.players[this.whoseTurn] == this.lastShotPlayer) ? [] : this.lastShotPoker, this.hintPoker);
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
            this.arrangePoker();
            btn.parent.destroy(true);
        }
        var group = this.add.group();
        if (this.players[this.whoseTurn] != this.lastShotPlayer) {
            var pass = new PokerGame.TextButton(this, this.world.width/2 - 80, this.world.height * 0.6, '不出', pass, this);
            group.add(pass);
        }
        var hint = new PokerGame.TextButton(this, this.world.width/2, this.world.height * 0.6, '提示', hint, this);
        group.add(hint);
        var shot = new PokerGame.TextButton(this, this.world.width/2 + 80, this.world.height * 0.6, '出牌', shot, this);
        group.add(shot);
        
        
        for (var i = 0; i < this.players[0].pokerInHand.length; i++) {
            var pokerid = this.players[0].pokerInHand[i];
            this.pokerDB[pokerid].inputEnabled = true;
        }
    }
    
};






