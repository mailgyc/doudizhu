PG.Player = function(pid, game) {
    this.pid = pid;
    this.seat = pid;
    this.game = game;
    
    this.pokerInHand = [];
    this.isLandlord = false;
    this.hasCalled = false;
    
}

PG.Player.prototype.hint = function(lastTurnPoker) {
    
    var cards, handCards = PG.Poker.toCards(this.pokerInHand);
    if (lastTurnPoker.length == 0) {
        cards = PG.Rule.bestShot(handCards);
    } else {
        cards = PG.Rule.cardsAbove(handCards, PG.Poker.toCards(lastTurnPoker));
    }
    
    return PG.Poker.toPoker(this.pokerInHand, cards);
    
}

PG.Player.prototype.canPlay = function(lastTurnPoker, shotPoker) {
    var cardsA = PG.Poker.toCards(shotPoker);
    var cardsB = PG.Poker.toCards(lastTurnPoker);
    var code = PG.Rule.compare(cardsA, cardsB);
    if (code == -10000)
        return -1;
    if (code > 0)
        return 1;
    return 0;
}

PG.Player.prototype.sortPoker = function() {
    this.pokerInHand.sort(PG.Poker.comparePoker);
}

PG.Player.prototype.playPoker = function(lastTurnPoker) {
    this.game.playerPlayPoker(lastTurnPoker);
}

PG.Player.prototype.removeAPoker = function (pid) {
    var length = this.pokerInHand.length;
    for(var i = 0; i < length; i++){
       if(this.pokerInHand[i] == pid){
            this.pokerInHand.splice(i, 1);
            break;
       }
    }
}

PG.NetPlayer = function(pid, game) {
    
    PG.Player.call(this, pid, game);
    
}

PG.NetPlayer.prototype = Object.create(PG.Player.prototype);
PG.NetPlayer.prototype.constructor = PG.NetPlayer;

PG.NetPlayer.prototype.playPoker = function(lastTurnPoker) {
}

PG.NetPlayer.prototype.removeAPoker = function (pid) {
    this.pokerInHand.pop();
};
