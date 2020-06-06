import Phaser from 'phaser'

export default class Poker extends Phaser.GameObjects.Sprite {

    constructor(scene, x, y, texture, frame) {
        super(scene, x, y, texture, frame);
        this.setOrigin(0.5);
        // this.id = id;
    }

    comparePoker(a, b) {
        if (a instanceof Array) {
            a = a[0];
            b = b[0];
        }

        if (a >= 52 || b >= 52) {
            return -(a - b);
        }
        a = a % 13;
        b = b % 13;
        if (a === 1 || a === 0) {
            a += 13;
        }
        if (b === 1 || b === 0) {
            b += 13;
        }
        return -(a - b);
    }

    toCards(pokers) {
        let cards = [];
        for (let i = 0; i < pokers.length; i++) {
            let pid = pokers[i];
            if (pid instanceof Array) {
                pid = pid[0];
            }
            if (pid === 52) {
                cards.push('W');
            } else if (pid === 53) {
                cards.push('w');
            } else {
                cards.push("A234567890JQK"[pid % 13]);
            }
        }
        return cards;

    }

    canCompare(pokersA, pokersB) {
        const cardsA = this.toCards(pokersA);
        const cardsB = this.toCards(pokersB);
        // return Rule.cardsValue(cardsA)[0] === Rule.cardsValue(cardsB)[0];
        return 0
    }

    toPokers(pokerInHands, cards) {
        let pokers = [];
        for (let i = 0; i < cards.length; i++) {
            let candidates = this.toPoker(cards[i]);
            for (let j = 0; j < candidates.length; j++) {
                if (pokerInHands.indexOf(candidates[j]) !== -1 && pokers.indexOf(candidates[j]) === -1) {
                    pokers.push(candidates[j]);
                    break
                }
            }
        }
        return pokers;
    }

    toPoker(card) {
        let cards = "A234567890JQK";
        for (let i = 0; i < 13; i++) {
            if (card === cards[i]) {
                return [i, i + 13, i + 13 * 2, i + 13 * 3];
            }
        }
        if (card === 'W') {
            return [52];
        } else if (card === 'w') {
            return [53];
        }
        return [54];

    }
}