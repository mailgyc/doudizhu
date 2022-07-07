
const PW = 90;
const PH = 120;

class Player {

    constructor(seat) {
        this.uid = seat;
        this.seat = seat;

        this.pokerInHand = [];
        this._pokerPic = {};
        this.isLandlord = false;

        this.hintPoker = [];
        this.isDraging = false;
    }


    cleanPokers() {
        let length = this.pokerInHand.length;
        for (let i = 0; i < length; i++) {
            let pid = this.pokerInHand[i];
            let p = this.findAPoker(pid);
            p.kill();
        }
        this.pokerInHand = [];
    }

    setLandlord() {
        this.isLandlord = true;
        this.head.setFrame('icon_landlord.png');
    };

    onInputDown(poker, pointer) {
        this.isDraging = true;
        this.onSelectPoker(poker, pointer);
    };

    onInputUp(poker, pointer) {
        this.isDraging = false;
        //this.onSelectPoker(poker, pointer);
    };

    onInputOver(poker, pointer) {
        if (this.isDraging) {
            this.onSelectPoker(poker, pointer);
        }
    };

    onSelectPoker(poker, pointer) {
        let index = this.hintPoker.indexOf(poker.id);
        if (index === -1) {
            poker.y = this.game.world.height - PH * 0.8;
            this.hintPoker.push(poker.id);
        } else {
            poker.y = this.game.world.height - PH * 0.5;
            this.hintPoker.splice(index, 1);
        }
    };

    onPass(btn) {
        this.game.finishPlay([]);
        this.pokerUnSelected(this.hintPoker);
        this.hintPoker = [];
        btn.parent.forEach(function (child) {
            child.kill();
        });
    };

    onHint(btn) {
        if (this.hintPoker.length == 0) {
            this.hintPoker = this.lastTurnPoker;
        } else {
            this.pokerUnSelected(this.hintPoker);
            if (this.lastTurnPoker.length > 0 && !Poker.canCompare(this.hintPoker, this.lastTurnPoker)) {
                this.hintPoker = [];
            }
        }
        let bigger = this.hint(this.hintPoker);
        if (bigger.length == 0) {
            if (this.hintPoker == this.lastTurnPoker) {
                this.say("没有能大过的牌");
            } else {
                this.pokerUnSelected(this.hintPoker);
            }
        } else {
            this.pokerSelected(bigger);
        }
        this.hintPoker = bigger;
    };

    onShot(btn) {
        if (this.hintPoker.length == 0) {
            return;
        }
        let code = this.canPlay(this.game.isLastShotPlayer() ? [] : this.game.tablePoker, this.hintPoker);
        if (code) {
            this.say(code);
            return;
        }
        this.game.finishPlay(this.hintPoker);
        this.hintPoker = [];
        btn.parent.forEach(function (child) {
            child.kill();
        });
    };


    hint(lastTurnPoker) {
        let cards;
        let handCards = Poker.toCards(this.pokerInHand);
        if (lastTurnPoker.length === 0) {
            cards = Rule.bestShot(handCards);
        } else {
            cards = Rule.cardsAbove(handCards, Poker.toCards(lastTurnPoker));
        }

        return Poker.toPokers(this.pokerInHand, cards);
    };

    canPlay(lastTurnPoker, shotPoker) {
        let cardsA = Poker.toCards(shotPoker);
        let valueA = Rule.cardsValue(cardsA);
        if (!valueA[0]) {
            return '出牌不合法';
        }
        let cardsB = Poker.toCards(lastTurnPoker);
        if (cardsB.length == 0) {
            return '';
        }
        let valueB = Rule.cardsValue(cardsB);
        if (valueA[0] != valueB[0] && valueA[1] < 1000) {
            return '出牌类型跟上家不一致';
        }

        if (valueA[1] > valueB[1]) {
            return '';
        }
        return '出牌需要大于上家';
    };

    playPoker(lastTurnPoker) {
        this.lastTurnPoker = lastTurnPoker;

        let group = this.shotLayer;
        let step = this.game.world.width / 6;
        let sx = this.game.world.width / 2 - 0.5 * step;
        if (!this.game.isLastShotPlayer()) {
            sx -= 0.5 * step;
            let pass = group.getAt(0);
            pass.centerX = sx;
            sx += step;
            pass.revive();
        }
        let hint = group.getAt(1);
        hint.centerX = sx;
        hint.revive();
        let shot = group.getAt(2);
        shot.centerX = sx + step;
        shot.revive();

        this.enableInput();
    };

    sortPoker() {
        this.pokerInHand.sort(Poker.comparePoker);
    };

    dealPoker() {
        this.sortPoker();
        let length = this.pokerInHand.length;
        for (let i = 0; i < length; i++) {
            let pid = this.pokerInHand[i];
            let p = new Poker(this.game, pid, pid);
            this.game.world.add(p);
            this.pushAPoker(p);
            this.dealPokerAnim(p, i);
        }
    };

    dealPokerAnim(p, i) {
        //to(properties, duration, ease, autoStart, delay, repeat, yoyo)
        this.game.add.tween(p).to({
            x: this.game.world.width / 2 + PW * 0.44 * (i - 8.5),
            y: this.game.world.height - PH / 2
        }, 500, Phaser.Easing.Default, true, 50 * i);
    };

    arrangePoker() {
        let count = this.pokerInHand.length;
        let gap = Math.min(this.game.world.width / count, PW * 0.44);
        for (let i = 0; i < count; i++) {
            let pid = this.pokerInHand[i];
            let p = this.findAPoker(pid);
            p.bringToTop();
            // this.add.tween(p).to({x: this.game.world.width / 2 + (i - count / 2) * gap}, 600, Phaser.Easing.Default, true);
        }
    };

    pushAPoker(poker) {
        this._pokerPic[poker.id] = poker;

        poker.events.onInputDown.add(this.onInputDown, this);
        poker.events.onInputUp.add(this.onInputUp, this);
        poker.events.onInputOver.add(this.onInputOver, this);
    };

    removeAPoker(pid) {
        let length = this.pokerInHand.length;
        for (let i = 0; i < length; i++) {
            if (this.pokerInHand[i] === pid) {
                this.pokerInHand.splice(i, 1);
                delete this._pokerPic[pid];
                return;
            }
        }
        console.log('Error: REMOVE POKER ', pid);
    };

    removeAllPoker() {
        let length = this.pokerInHand.length;
        for (let i = 0; i < length; i++) {
            this.pokerInHand.splice(i, 1);
            delete this._pokerPic[pid];
        }
        console.log('Error: REMOVE POKER ', pid);
    };


    findAPoker(pid) {
        let poker = this._pokerPic[pid];
        if (poker === undefined) {
            console.log('Error: FIND POKER ', pid);
        }
        return poker;
    };

    enableInput() {
        let length = this.pokerInHand.length;
        for (let i = 0; i < length; i++) {
            let p = this.findAPoker(this.pokerInHand[i]);
            p.inputEnabled = true;
        }
    };

    pokerSelected(pokers) {
        for (let i = 0; i < pokers.length; i++) {
            let p = this.findAPoker(pokers[i]);
            p.y = this.game.world.height - PH * 0.8;
        }
    };

    pokerUnSelected(pokers) {
        for (let i = 0; i < pokers.length; i++) {
            let p = this.findAPoker(pokers[i]);
            p.y = this.game.world.height - PH / 2;
        }
    };
}
