PG.Poker = function (game, id, frame) {

    Phaser.Sprite.call(this, game, game.world.width / 2, game.world.height * 0.4, 'poker', frame);

    this.anchor.set(0.5);
    this.id = id;

    return this;
};

PG.Poker.prototype = Object.create(Phaser.Sprite.prototype);
PG.Poker.prototype.constructor = PG.Poker;

PG.Poker.comparePoker = function (a, b) {

    if (a instanceof Array) {
        a = a[0];
        b = b[0];
    }


    if (a >= 52 || b >= 52) {
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
};

PG.Poker.toCards = function (pokers) {
    var cards = [];
    for (var i = 0; i < pokers.length; i++) {
        var pid = pokers[i];
        if (pid instanceof Array) {
            pid = pid[0];
        }
        if (pid == 52) {
            cards.push('W');
        } else if (pid == 53) {
            cards.push('w');
        } else {
            cards.push("A234567890JQK"[pid % 13]);
        }
    }
    return cards;

};

PG.Poker.canCompare = function (pokersA, pokersB) {
    var cardsA = this.toCards(pokersA);
    var cardsB = this.toCards(pokersB);
    return PG.Rule.cardsValue(cardsA)[0] == PG.Rule.cardsValue(cardsB)[0];
};

PG.Poker.toPokers = function (pokerInHands, cards) {
    var pokers = [];
    for (var i = 0; i < cards.length; i++) {
        var candidates = this.toPoker(cards[i]);
        for (var j = 0; j < candidates.length; j++) {
            if (pokerInHands.indexOf(candidates[j]) != -1 && pokers.indexOf(candidates[j]) == -1) {
                pokers.push(candidates[j]);
                break
            }
        }
    }
    return pokers;
};

PG.Poker.toPoker = function (card) {

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

};

PG.Rule = {};

PG.Rule.cardsAbove = function (handCards, turnCards) {

    var turnValue = this.cardsValue(turnCards);
    if (turnValue[0] == '') {
        return '';
    }
    handCards.sort(this.sorter);
    var oneRule = PG.RuleList[turnValue[0]];
    for (var i = turnValue[1] + 1; i < oneRule.length; i++) {
        if (this.containsAll(handCards, oneRule[i])) {
            return oneRule[i];
        }
    }

    if (turnValue[1] < 1000) {
        oneRule = PG.RuleList['bomb'];
        for (var i = 0; i < oneRule.length; i++) {
            if (this.containsAll(handCards, oneRule[i])) {
                return oneRule[i];
            }
        }
        if (this.containsAll(handCards, 'wW')) {
            return 'wW';
        }
    }

    return '';
};

PG.Rule.bestShot = function (handCards) {

    handCards.sort(this.sorter);
    var shot = '';
    var len = this._CardsType.length;
    for (var i = 2; i < len; i++) {
        var oneRule = PG.RuleList[this._CardsType[i]];
        for (var j = 0; j < oneRule.length; j++) {
            if (oneRule[j].length > shot.length && this.containsAll(handCards, oneRule[j])) {
                shot = oneRule[j];
            }
        }
    }

    if (shot == '') {
        oneRule = PG.RuleList['bomb'];
        for (var i = 0; i < oneRule.length; i++) {
            if (this.containsAll(handCards, oneRule[i])) {
                return oneRule[i];
            }
        }
        if (this.containsAll(handCards, 'wW'))
            return 'wW';
    }

    return shot;
};

PG.Rule._CardsType = [
    'rocket', 'bomb',
    'single', 'pair', 'trio', 'trio_pair', 'trio_single',
    'seq_single5', 'seq_single6', 'seq_single7', 'seq_single8', 'seq_single9', 'seq_single10', 'seq_single11', 'seq_single12',
    'seq_pair3', 'seq_pair4', 'seq_pair5', 'seq_pair6', 'seq_pair7', 'seq_pair8', 'seq_pair9', 'seq_pair10',
    'seq_trio2', 'seq_trio3', 'seq_trio4', 'seq_trio5', 'seq_trio6',
    'seq_trio_pair2', 'seq_trio_pair3', 'seq_trio_pair4', 'seq_trio_pair5',
    'seq_trio_single2', 'seq_trio_single3', 'seq_trio_single4', 'seq_trio_single5',
    'bomb_pair', 'bomb_single'];

PG.Rule.sorter = function (a, b) {
    var card_str = '34567890JQKA2wW';
    return card_str.indexOf(a) - card_str.indexOf(b);
};

PG.Rule.index_of = function (array, ele) {
    if (array[0].length != ele.length) {
        return -1;
    }
    for (var i = 0, l = array.length; i < l; i++) {
        if (array[i] == ele) {
            return i;
        }
    }
    return -1;
};

PG.Rule.containsAll = function (parent, child) {
    var index = 0;
    for (var i = 0, l = child.length; i < l; i++) {
        index = parent.indexOf(child[i], index);
        if (index == -1) {
            return false;
        }
        index += 1;
    }
    return true;
};

PG.Rule.cardsValue = function (cards) {

    if (typeof(cards) != 'string') {
        cards.sort(this.sorter);
        cards = cards.join('');
    }

    if (cards == 'wW')
        return ['rocket', 2000];

    var index = this.index_of(PG.RuleList['bomb'], cards);
    if (index >= 0)
        return ['bomb', 1000 + index];

    var length = this._CardsType.length;
    for (var i = 2; i < length; i++) {
        var typeName = this._CardsType[i];
        var index = this.index_of(PG.RuleList[typeName], cards);
        if (index >= 0)
            return [typeName, index];
    }
    console.log('Error: UNKNOWN TYPE ', cards);
    return ['', 0];
};

PG.Rule.compare = function (cardsA, cardsB) {

    if (cardsA.length == 0 && cardsB.length == 0) {
        return 0;
    }
    if (cardsA.length == 0) {
        return -1;
    }
    if (cardsB.length == 0) {
        return 1;
    }

    var valueA = this.cardsValue(cardsA);
    var valueB = this.cardsValue(cardsB);

    if ((valueA[1] < 1000 && valueB[1] < 1000) && (valueA[0] != valueB[0])) {
        console.log('Error: Compare ', cardsA, cardsB);
    }

    return valueA[1] - valueB[1];
};

PG.Rule.shufflePoker = function () {
    var pokers = [];
    for (var i = 0; i < 54; i++) {
        pokers.push(i);
    }

    var currentIndex = pokers.length, temporaryValue, randomIndex;
    while (0 != currentIndex) {
        randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex -= 1;

        temporaryValue = pokers[currentIndex];
        pokers[currentIndex] = pokers[randomIndex];
        pokers[randomIndex] = temporaryValue;
    }
    return pokers;
}
;

