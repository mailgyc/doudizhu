PokerGame.Poker = function(game, id, frame) {
    
    Phaser.Sprite.call(this, game, game.world.width/2, game.world.height * 0.4, 'poker', frame);

    this.anchor.set(0.5);
    this.id = id;
    
    return this;
}

PokerGame.Poker.prototype = Object.create(Phaser.Sprite.prototype);
PokerGame.Poker.prototype.constructor = PokerGame.Poker;

PokerGame.Poker.comparePoker = function(a, b) {

    if (a instanceof Array) {
        a = a[0];
        b = b[0];
    }


    if (a >=52 || b >= 52) {
        return -(a - b);
    }
    a = a % 13;
    b = b % 13;
    if (a == 1 || a == 0) {
        a += 13;
    }
    if (b == 1 || b == 0) {
        b += 13;
    }
    return -(a - b);
}

PokerGame.Poker.toCards = function(pokers) {

    var cards = [];
    for (var i = 0; i < pokers.length; i++) {
        var pid = pokers[i];
        if (pid instanceof Array) {
            pid = pid[0];
        }
        if (pid== 52) {
            cards.push('W');
        } else if (pid == 53) {
            cards.push('w');
        } else {
            cards.push("A234567890JQK"[pid%13]);
        }
    }
    return cards;
    
}

PokerGame.Poker.toPoker = function(card) {
    
    var cards = "A234567890JQK";
    for (var i = 0; i < 13; i++) {
        if (card == cards[i]) {
            return [i, i + 13, i + 13 * 2, i + 13 * 3];
        }
    }
    if (card == 'W') {
        return [52];
    } else if (card == 'w') {
        return [53];
    }
    return [54];
    
}

