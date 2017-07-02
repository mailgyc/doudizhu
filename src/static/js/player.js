PG.Player = function (pid, game) {
    this.pid = pid;
    this.seat = 0;
    this.game = game;

    this.pokerInHand = [];
    this._pokerPic = {};
    this.isLandlord = false;
};

PG.Player.prototype.hint = function (lastTurnPoker) {

    var cards;
    var handCards = PG.Poker.toCards(this.pokerInHand);
    if (lastTurnPoker.length === 0) {
        cards = PG.Rule.bestShot(handCards);
    } else {
        cards = PG.Rule.cardsAbove(handCards, PG.Poker.toCards(lastTurnPoker));
    }

    return PG.Poker.toPokers(this.pokerInHand, cards);
};

PG.Player.prototype.canPlay = function (lastTurnPoker, shotPoker) {
    var cardsA = PG.Poker.toCards(shotPoker);
    var cardsB = PG.Poker.toCards(lastTurnPoker);
    var code = PG.Rule.compare(cardsA, cardsB);
    if (code === -10000)
        return -1;
    if (code > 0)
        return 1;
    return 0;
};

PG.Player.prototype.sortPoker = function () {
    this.pokerInHand.sort(PG.Poker.comparePoker);
};

PG.Player.prototype.pushAPoker = function (poker) {
    this._pokerPic[poker.id] = poker;
};

PG.Player.prototype.removeAPoker = function (pid) {
    var length = this.pokerInHand.length;
    for (var i = 0; i < length; i++) {
        if (this.pokerInHand[i] === pid) {
            this.pokerInHand.splice(i, 1);
            delete this._pokerPic[pid];
            return true;
        }
    }
    console.log('Error: REMOVE POKER ', pid);
    return false;
};

PG.Player.prototype.findAPoker = function (pid) {
    var poker = this._pokerPic[pid];
    if (poker === undefined) {
        console.log('Error: FIND POKER ', pid);
    }
    return poker;
};

PG.Player.prototype.enableInput = function () {
    var length = this.pokerInHand.length;
    for (var i = 0; i < length; i++) {
        var p = this.findAPoker(this.pokerInHand[i]);
        p.inputEnabled = true;
    }
};

PG.Player.prototype.pokerSelected = function (pokers) {
    for (var i = 0; i < pokers.length; i++) {
        var p = this.findAPoker(pokers[i]);
        p.y = this.game.world.height - PG.PH * 0.8;
    }
};

PG.Player.prototype.pokerUnSelected = function (pokers) {
    for (var i = 0; i < pokers.length; i++) {
        var p = this.findAPoker(pokers[i]);
        p.y = this.game.world.height - PG.PH / 2;
    }
};


PG.NetPlayer = function (pid, game) {
    PG.Player.call(this, pid, game);
    this._pokerPic = [];
};

PG.NetPlayer.prototype = Object.create(PG.Player.prototype);
PG.NetPlayer.prototype.constructor = PG.NetPlayer;

PG.NetPlayer.prototype.pushAPoker = function (poker) {
    this._pokerPic.push(poker);
};

PG.NetPlayer.prototype.removeAPoker = function (pid) {
    this.pokerInHand.pop();
    this._pokerPic.pop();
};

PG.NetPlayer.prototype.findAPoker = function (pid) {
    return this._pokerPic[this._pokerPic.length - 1];
};
