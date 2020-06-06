
const cardsValue = function (cards: string) {

    if (typeof (cards) != 'string') {
        cards.sort(this.sorter);
        cards = cards.join('');
    }

    if (cards === 'wW')
        return ['rocket', 2000];

    let index = this.findCardType(RuleList['bomb'], cards);
    if (index >= 0)
        return ['bomb', 1000 + index];

    let length = CARD_TYPES.length;
    for (let i = 2; i < length; i++) {
        const typeName = CARD_TYPES[i];
        const index = this.findCardType(RuleList[typeName], cards);
        if (index >= 0)
            return [typeName, index];
    }
    console.log('Error: UNKNOWN TYPE ', cards);
    return ['', 0];
};


const cardsAbove = function (RuleList: any, handCards: Array<string>, turnCards: Array<string>) {

    const turnValue = cardsValue(turnCards);
    if (turnValue[0] === '') {
        return '';
    }
    handCards.sort(this.sorter);
    const oneRule = RuleList[turnValue[0]];
    for (let i = turnValue[1] + 1; i < oneRule.length; i++) {
        if (this.containsAll(handCards, oneRule[i])) {
            return oneRule[i];
        }
    }

    if (turnValue[1] < 1000) {
        const oneRule = RuleList['bomb'];
        for (let i = 0; i < oneRule.length; i++) {
            if (containsAll(handCards, oneRule[i])) {
                return oneRule[i];
            }
        }
        if (containsAll(handCards, 'wW')) {
            return 'wW';
        }
    }

    return '';
};

const bestShot = function (RuleList: Array<Array<string>>, handCards: Array<string>) {

    handCards.sort(this.sorter);
    let shot = '';
    for (let i = 2; i < CARD_TYPES.length; i++) {
        const oneRule = RuleList[CARD_TYPES[i]];
        for (let j = 0; j < oneRule.length; j++) {
            if (oneRule[j].length > shot.length && this.containsAll(handCards, oneRule[j])) {
                shot = oneRule[j];
            }
        }
    }

    if (shot === '') {
        const oneRule = RuleList['bomb'];
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

const CARD_TYPES: Array<string> = [
    'rocket', 'bomb',
    'single', 'pair', 'trio', 'trio_pair', 'trio_single',
    'seq_single5', 'seq_single6', 'seq_single7', 'seq_single8', 'seq_single9', 'seq_single10', 'seq_single11', 'seq_single12',
    'seq_pair3', 'seq_pair4', 'seq_pair5', 'seq_pair6', 'seq_pair7', 'seq_pair8', 'seq_pair9', 'seq_pair10',
    'seq_trio2', 'seq_trio3', 'seq_trio4', 'seq_trio5', 'seq_trio6',
    'seq_trio_pair2', 'seq_trio_pair3', 'seq_trio_pair4', 'seq_trio_pair5',
    'seq_trio_single2', 'seq_trio_single3', 'seq_trio_single4', 'seq_trio_single5',
    'bomb_pair', 'bomb_single'];

const sorter = function (a: string, b: string): number {
    const card_str = '34567890JQKA2wW';
    return card_str.indexOf(a) - card_str.indexOf(b);
};

const findCardType = function (cardTypes: Array<string>, target: string) {
    if (cardTypes[0].length !== target.length) {
        return -1;
    }
    for (let i = 0; i < cardTypes.length; i++) {
        if (cardTypes[i] === target) {
            return i;
        }
    }
    return -1;
};

const containsAll = function (parent: Array<string>, child: string) {
    let index = 0;
    for (let i = 0, l = child.length; i < l; i++) {
        index = parent.indexOf(child[i], index);
        if (index === -1) {
            return false;
        }
        index += 1;
    }
    return true;
};

const compare = function (cardsA: string, cardsB: string) {

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

    if ((valueA[1] < 1000 && valueB[1] < 1000) && (valueA[0] !== valueB[0])) {
        console.log('Error: Compare ', cardsA, cardsB);
    }

    return valueA[1] - valueB[1];
};

const shufflePoker = function () {
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
};

