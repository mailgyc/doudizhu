// A 2 3 4 5 6 7 8 9 0 J Q K W w

// 记分
// 　　地主先出完所有的牌就赢了，如果没有出过炸弹或火箭，那么每个农民要把定约的分数(1分、2分或3分)付给地主。两个农民中有一个先出完所有的牌，地主就输了，那么地主要把定约的分数付给每个农民。
//     每当任何一个玩家出了炸弹或火箭，那么分数就要翻一番。例如某局牌出了2个炸弹和1个火箭，叫3分的地主如果先出完，他就向每个农民赢得24分【总共赢得48分】，如果农民先出完，地主就向每个农民输掉24分【总共输掉48分】。
// 　　这里要注意，两个农民赢的分数或输的分数是一样的，他们构成一个临时的同盟。对抗地主时，帮助同伴先出完等同于自己先出完。因此两个农民最好不要经常盖过彼此的牌，而较弱的农民应该帮助较强的农民先出完。

PokerGame.Rule = {
}

PokerGame.Rule.cardsAbove = function(handCards, turnCards) {
    
    var pair = this.cardsValue(turnCards);
    if (pair.type == '')
        return '';
    
    handCards.sort(this.sortfunc);
    var oneRule = this.ruleList[pair.type];
    for (var i = 0; i < oneRule.length; i++) {
        if (i > pair.value && this.containsAll(handCards, oneRule[i])) {
            return oneRule[i];
        }
    }
    if (pair.value < 1000) {
        oneRule = this.ruleList['bomb'];
        for (var i = 0; i < oneRule.length; i++) {
            if (this.containsAll(handCards, oneRule[i])) {
                return oneRule[i];
            }
        }
        if (this.containsAll(handCards, 'wW'))
            return 'wW';
    }
    return '';
}

PokerGame.Rule.bestShot = function(handCards) {
    
    handCards.sort(this.sortfunc);
    var shot = '';
    var len = this.cardsType.length;
    for (var i = 2; i < len; i++) {
        var oneRule = this.ruleList[this.cardsType[i]];
        for (var j = 0; j < oneRule.length; j++) {
            if (oneRule[j].length > shot.length && this.containsAll(handCards, oneRule[j])) {
                shot = oneRule[j];
            }
        }
    }
    
    if (shot == '') {
        oneRule = this.ruleList['bomb'];
        for (var i = 0; i < oneRule.length; i++) {
            if (this.containsAll(handCards, oneRule[i])) {
                return oneRule[i];
            }
        }
        if (this.containsAll(handCards, 'wW'))
            return 'wW';
    }

    return shot;
}

PokerGame.Rule.sortfunc = function(a, b) {
    var cardstr = '34567890JQKA2wW';
    return cardstr.indexOf(a) - cardstr.indexOf(b);
}

PokerGame.Rule.cardsType = [
    'rocket', 'bomb',
    'single', 'pair', 'trio', 'trio_pair', 'trio_single',
    'seq_single5', 'seq_single6', 'seq_single7', 'seq_single8', 'seq_single9', 'seq_single10', 'seq_single11', 'seq_single12',
    'seq_pair3', 'seq_pair4', 'seq_pair5', 'seq_pair6', 'seq_pair7', 'seq_pair8', 'seq_pair9', 'seq_pair10',
    'seq_trio2', 'seq_trio3', 'seq_trio4', 'seq_trio5', 'seq_trio6',
    'seq_trio_pair2', 'seq_trio_pair3', 'seq_trio_pair4', 'seq_trio_pair5',
    'seq_trio_single2', 'seq_trio_single3', 'seq_trio_single4', 'seq_trio_single5',
    'bomb_pair', 'bomb_single' ];

PokerGame.Rule.cardsValue = function(cards) {
    
    if (typeof(cards) != 'string') {
        cards.sort(this.sortfunc);
        cards = cards.join('');
    }
    
    function find(array, ele) {
        if (array[0].length != ele.length) {
            return -1;
        }
        for (var i = 0, l = array.length; i < l; i++) {
            if (array[i] == ele) {
                return i;
            }
        }
        return -1;
    }
    
    if (cards == 'wW')
        return {'type': 'rocket', 'value': 2000};
    
    var value = find(this.ruleList['bomb'], cards);
    if (value >= 0)
        return {'type': 'bomb', 'value': 1000 + value};
    
    var len = this.cardsType.length;
    var typeName;
    for (var i = 2; i < len; i++) {
        typeName = this.cardsType[i];
        value = find(this.ruleList[typeName], cards);
        if (value >= 0)
            return {'type': typeName, 'value': value};
    }
    return {'type': '', 'value': 0};
}

PokerGame.Rule.compare = function(cardsA, cardsB) {

    var valueA = this.cardsValue(cardsA);
    if (valueA.type == '') {
        return -10000;
    }
    var valueB = this.cardsValue(cardsB);
    if (valueA.type == valueB.type) {
        return valueA.value - valueB.value;
    }
    if (valueA.value >= 1000) {
        return valueA.value - valueB.value;
    } else {
        return 0;
    }
    
}

PokerGame.Rule.containsAll = function(parent, child) {
    var index = 0;
    for (var i = 0, l = child.length; i < l; i++) {
        index = parent.indexOf(child[i], index);
        if (index == -1) {
            return false;
        }
        index += 1;
    }
    return true;
}