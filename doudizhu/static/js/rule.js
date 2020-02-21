PG.Poker = function (game, id, frame) {

    Phaser.Sprite.call(this, game, game.world.width / 2, game.world.height * 0.4, 'poker', frame - 1);

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


    if (a > 52 || b > 52) {
        return -(a - b);
    }
    a = a % 13;
    b = b % 13;
    if (a <= 2) {
        a += 13;
    }
    if (b <= 2) {
        b += 13;
    }
    return -(a - b);
};

PG.Poker.toCards = function (pokers) {
    let cards = [];
    for (let i = 0; i < pokers.length; i++) {
        let pid = pokers[i];
        if (pid instanceof Array) {
            pid = pid[0];
        }
        if (pid === 53) {
            cards.push('w');
        } else if (pid === 54) {
            cards.push('W');
        } else {
            cards.push("KA234567890JQ"[pid % 13]);
        }
    }
    return cards;

};

PG.Poker.canCompare = function (pokersA, pokersB) {
    let cardsA = this.toCards(pokersA);
    let cardsB = this.toCards(pokersB);
    return PG.Rule.cardsValue(cardsA)[0] == PG.Rule.cardsValue(cardsB)[0];
};

PG.Poker.toPokers = function (pokerInHands, cards) {
    let pokers = [];
    for (let i = 0; i < cards.length; i++) {
        let candidates = this.toPoker(cards[i]);
        for (let j = 0; j < candidates.length; j++) {
            if (pokerInHands.indexOf(candidates[j]) != -1 && pokers.indexOf(candidates[j]) == -1) {
                pokers.push(candidates[j]);
                break
            }
        }
    }
    return pokers;
};

PG.Poker.toPoker = function (card) {

    const cards = "?A234567890JQK";
    for (let i = 1; i < cards.length; i++) {
        if (card === cards[i]) {
            return [i, i + 13, i + 26, i + 39];
        }
    }
    if (card === 'w') {
        return [53];
    } else if (card === 'W') {
        return [54];
    }
    return [55];

};

PG.Rule = {};

PG.Rule.cardsAbove = function (handCards, turnCards) {

    let turnValue = this.cardsValue(turnCards);
    if (turnValue[0] === '') {
        return '';
    }
    handCards.sort(this.sorter);
    let oneRule = PG.RuleList[turnValue[0]];
    for (let i = turnValue[1] + 1; i < oneRule.length; i++) {
        if (this.containsAll(handCards, oneRule[i])) {
            return oneRule[i];
        }
    }

    if (turnValue[1] < 10000) {
        oneRule = PG.RuleList['bomb'];
        for (let i = 0; i < oneRule.length; i++) {
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
    let shot = '';
    for (let i = 2; i < this._CardsType.length; i++) {
        let oneRule = PG.RuleList[this._CardsType[i]];
        for (let j = 0; j < oneRule.length; j++) {
            if (oneRule[j].length > shot.length && this.containsAll(handCards, oneRule[j])) {
                shot = oneRule[j];
            }
        }
    }

    if (shot === '') {
        oneRule = PG.RuleList['bomb'];
        for (let i = 0; i < oneRule.length; i++) {
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
    'seq_trio_pair2', 'seq_trio_pair3', 'seq_trio_pair4',
    'seq_trio_single2', 'seq_trio_single3', 'seq_trio_single4', 'seq_trio_single5',
    'bomb_pair', 'bomb_single'];

PG.Rule.sorter = function (a, b) {
    let card_str = '34567890JQKA2wW';
    return card_str.indexOf(a) - card_str.indexOf(b);
};

PG.Rule.index_of = function (array, ele) {
    if (array[0].length !== ele.length) {
        return -1;
    }
    for (let i = 0, l = array.length; i < l; i++) {
        if (array[i] === ele) {
            return i;
        }
    }
    return -1;
};

PG.Rule.containsAll = function (parent, child) {
    let index = 0;
    for (let i = 0; i < child.length; i++) {
        index = parent.indexOf(child[i], index);
        if (index === -1) {
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

    if (cards === 'wW')
        return ['rocket', 20000];

    let index = this.index_of(PG.RuleList['bomb'], cards);
    if (index >= 0)
        return ['bomb', 10000 + index];

    let length = this._CardsType.length;
    for (let i = 2; i < length; i++) {
        let typeName = this._CardsType[i];
        let index = this.index_of(PG.RuleList[typeName], cards);
        if (index >= 0)
            return [typeName, index];
    }
    console.log('Error: UNKNOWN TYPE ', cards);
    return ['', 0];
};

PG.Rule.compare = function (cardsA, cardsB) {

    if (cardsA.length === 0 && cardsB.length === 0) {
        return 0;
    }
    if (cardsA.length === 0) {
        return -1;
    }
    if (cardsB.length === 0) {
        return 1;
    }

    let valueA = this.cardsValue(cardsA);
    let valueB = this.cardsValue(cardsB);

    if ((valueA[1] < 10000 && valueB[1] < 10000) && (valueA[0] !== valueB[0])) {
        console.log('Error: Compare ', cardsA, cardsB);
    }

    return valueA[1] - valueB[1];
};

PG.Rule.shufflePoker = function () {
    let pokers = [];
    for (let i = 0; i < 54; i++) {
        pokers.push(i);
    }

    let currentIndex = pokers.length, temporaryValue, randomIndex;
    while (0 !== currentIndex) {
        randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex -= 1;

        temporaryValue = pokers[currentIndex];
        pokers[currentIndex] = pokers[randomIndex];
        pokers[randomIndex] = temporaryValue;
    }
    return pokers;
}
;

