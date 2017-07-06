
PG.NetPlayer = function (seat, game) {
    PG.Player.call(this, seat, game);
    this._pokerPic = [];
};

PG.NetPlayer.prototype = Object.create(PG.Player.prototype);
PG.NetPlayer.prototype.constructor = PG.NetPlayer;

PG.NetPlayer.prototype.pushAPoker = function (poker) {
    this._pokerPic.push(poker);
    this.updateLeftPoker();
};

PG.NetPlayer.prototype.removeAPoker = function (pid) {
    this.pokerInHand.pop();
    this._pokerPic.pop();
    this.updateLeftPoker();
};

PG.NetPlayer.prototype.findAPoker = function (pid) {
    return this._pokerPic[this._pokerPic.length - 1];
};

PG.NetPlayer.prototype.initUI = function (sx, sy) {
    PG.Player.prototype.initUI.call(this, sx, sy);
    var style = {font: "22px Arial", fill: "#ffffff", align: "center"};
    this.uiLeftPoker = this.game.add.text(sx, sy + PG.PH + 10, '17', style);
    this.uiLeftPoker.anchor.set(0.5, 0);
    this.uiLeftPoker.kill();

    var style = {font: "20px Arial", fill: "#c8c8c8", align: "center"};
    if (this.seat == 1) {
        this.uiName = this.game.add.text(sx - 40, sy - 80, '等待玩家加入', style);
        this.uiName.anchor.set(1, 0);
    } else {
        this.uiName = this.game.add.text(sx + 40, sy - 80, '等待玩家加入', style);
        this.uiName.anchor.set(0, 0);
    }
};


PG.NetPlayer.prototype.updateInfo = function (uid, name) {
    PG.Player.prototype.updateInfo.call(this, uid, name);
    if (uid == -1) {
        this.uiName.text = '等待玩家加入';
    } else {
        this.uiName.text = name;
    }
};

PG.NetPlayer.prototype.updateLeftPoker = function () {
    var len = this.pokerInHand.length;
    if (len > 0) {
        this.uiLeftPoker.text = "" + this.pokerInHand.length;
        this.uiLeftPoker.revive();
    } else {
        this.uiLeftPoker.kill();
    }
};
