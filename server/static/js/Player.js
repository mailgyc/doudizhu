PokerGame.Player = function(pid, game) {
    this.pid = pid;
    this.seat = pid;
    this.game = game;
    
    this.pokerInHand = [];
    this.isLandlord = false;
    this.hasCalled = false;
    
}

PokerGame.Player.prototype.fetchAPoker = function(pid, poker) {
    this.pokerInHand.push([pid, poker]);
}

PokerGame.Player.prototype.getPoker = function(index) {
    return this.pokerInHand[index];
}

PokerGame.Player.prototype.findPoker = function(pid) {
    var length = this.pokerInHand.length;
    for (var i = 0; i < length; i++) {
        if (this.pokerInHand[i][0] == pid) {
            return this.pokerInHand[i][1];
        }
    }
    return this.pokerInHand[0][1];
}

PokerGame.Player.prototype.sortPoker = function() {
    this.pokerInHand.sort(PokerGame.Poker.comparePoker);
}

PokerGame.Player.prototype.startCallScore = function(minscore) {
    this.game.playerCallScore(minscore);
}

PokerGame.Player.prototype.hint = function(lastTurnPoker) {
    
    function contains(arr, ele) {
        var length = arr.length;
        for (var i = 0; i < length; i++) {
            if (arr[i][0] == ele) {
                return true;
            }
        }
        return false;
    }

    var cards, handCards = PokerGame.Poker.toCards(this.pokerInHand);
    if (lastTurnPoker.length == 0) {
        cards = PokerGame.Rule.bestShot(handCards);
    } else {
        cards = PokerGame.Rule.cardsAbove(handCards, PokerGame.Poker.toCards(lastTurnPoker));
    }
    
    var pokers = [];
    for (var i = 0; i < cards.length; i++) {
        var options = PokerGame.Poker.toPoker(cards[i]);
        for (var j = 0; j < options.length; j++) {
            if ( !contains(pokers, options[j]) && contains(this.pokerInHand, options[j])) {
                pokers.push([options[j], this.findPoker(options[j])]);
                break;
            }
        }
        if (j == options.length) {
            alert('not found ' + cards[i]);
        }
    }

    return pokers;
    
}

PokerGame.Player.prototype.canPlay = function(lastTurnPoker, shotPoker) {
    var cardsA = PokerGame.Poker.toCards(shotPoker);
    var cardsB = PokerGame.Poker.toCards(lastTurnPoker);
    var code = PokerGame.Rule.compare(cardsA, cardsB);
    if (code == -10000)
        return -1;
    if (code > 0)
        return 1;
    return 0;
}

PokerGame.Player.prototype.playPoker = function(lastTurnPoker) {
    this.game.playerPlayPoker(lastTurnPoker);
}

PokerGame.Player.prototype.removeAPoker = function (pid) {
    var length = this.pokerInHand.length;
    for(var i = 0; i < length; i++){
       if(this.pokerInHand[i][0] == pid){
            this.pokerInHand.splice(i, 1);
            break;
       }
    }
}

PokerGame.NetPlayer = function(pid, game) {
    
    PokerGame.Player.call(this, pid, game);
    
}

PokerGame.NetPlayer.prototype = Object.create(PokerGame.Player.prototype);
PokerGame.NetPlayer.prototype.constructor = PokerGame.NetPlayer;

PokerGame.NetPlayer.prototype.startCallScore = function (minscore) {
}

PokerGame.NetPlayer.prototype.playPoker = function(lastTurnPoker) {
}

PokerGame.NetPlayer.prototype.removeAPoker = function (pid) {
    this.pokerInHand.pop();
}

PokerGame.AIPlayer = function(pid, game) {
    
    PokerGame.Player.call(this, pid, game);
    
}

PokerGame.AIPlayer.prototype = Object.create(PokerGame.Player.prototype);
PokerGame.AIPlayer.prototype.constructor = PokerGame.AIPlayer;

PokerGame.AIPlayer.prototype.startCallScore = function (minscore) {
    var millisTime = this.game.rnd.integerInRange(1000, 2000);
    var score = this.game.rnd.integerInRange(minscore + 1, 3);
    this.hasCalled = true;
    this.game.time.events.add(millisTime, this.game.finishCallScore, this.game, score);
}

PokerGame.AIPlayer.prototype.playPoker = function(lastTurnPoker) {
    
    var pokers = this.hint(lastTurnPoker);
    var millisTime = this.game.rnd.integerInRange(100, 1000);
    this.game.time.events.add(millisTime, this.game.finishPlay, this.game, pokers);
}
