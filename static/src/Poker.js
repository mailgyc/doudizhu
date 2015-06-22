PokerGame.Poker = function(game, id, frame) {
    
    Phaser.Sprite.call(this, game, game.world.width/2, game.world.height * 0.4, 'poker', frame);

    this.anchor.set(0.5);
    this.id = id;
    
    return this;
}

PokerGame.Poker.prototype = Object.create(Phaser.Sprite.prototype);
PokerGame.Poker.prototype.constructor = PokerGame.Poker;

PokerGame.Poker.comparePoker = function(a, b) {
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
        if (pokers[i] == 52) {
            cards.push('W');
        } else if (pokers[i] == 53) {
            cards.push('w');
        } else {
            cards.push("A234567890JQK"[pokers[i]%13]);
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

PokerGame.Poker.toPokers = function(existPokers, cards) {

    var pokers = [];
    var i, j;
    for (i = 0; i < cards.length; i++) {
        var options = PokerGame.Poker.toPoker(cards[i]);
        for (j = 0; j < options.length; j++) {
            if (pokers.indexOf(options[j]) == -1 && existPokers.indexOf(options[j]) != -1) {
                pokers.push(options[j]);
                break;
            }
        }
        if (j == options.length) {
            alert('not found ' + cards[i]);
        }
    }
    return pokers;

}