
PokerGame.MainMenu = function (game) {
};

PokerGame.MainMenu.prototype = {

	create: function () {

		this.stage.backgroundColor = '#182d3b';
		
		var bg = this.add.sprite(this.game.width/2, 0, 'bg_1');
		bg.anchor.set(0.5, 0);
		
		var start = this.add.button(this.world.width/2, this.world.height/4, 'button', this.startGame, this, 'start.png', 'start.png', 'start.png');
		start.anchor.set(0.5);
		this.world.add(start);
		
		var room = this.add.button(this.world.width/2, this.world.height/2, 'button', this.gotoRoom, this, 'settings.png', 'settings.png', 'settings.png');
		room.anchor.set(0.5);
		this.world.add(room);
		
		var reg = this.add.button(this.world.width/2, this.world.height * 3/4, 'button', this.gotoReg, this, 'intro.png', 'intro.png', 'intro.png');
		reg.anchor.set(0.5);
		this.world.add(reg);
	},

	update: function () {

	},

	startGame: function () {
		PokerGame.gameType = 0;
		this.state.start('Game');
		//this.music.stop();
	},
	
	gotoRoom: function () {
		PokerGame.gameType = 1;
		this.state.start('Game')
		// var style = { font: "22px Arial", fill: "#ffffff", align: "center" };
		// var text = this.add.text(0, 0, "ha ha ha ha", style);
		// var tween = this.add.tween(text).to( { x: 600, y: 450 }, 2000, "Linear", true);
		// function destroy() {
		// 	text.destroy();
		// }
		// tween.onComplete.add(destroy, this);
	},
	
	gotoReg: function () {
		var style = { font: "22px Arial", fill: "#ffffff", align: "center" };
		var text = this.add.text(0, 0, "hei hei hei hei", style);
		var tween = this.add.tween(text).to( { x: 600, y: 450 }, 2000, "Linear", true);
		//tween.onComplete.add(text.destroy, text);
		tween.onComplete.add(Phaser.Text.prototype.destroy, text);
	}

};
