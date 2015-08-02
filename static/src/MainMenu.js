
PokerGame.MainMenu = function (game) {

	this.music = null;

};

PokerGame.MainMenu.prototype = {

	create: function () {

		this.stage.backgroundColor = '#182d3b';

		//this.music = this.add.audio('bg_music');
		//this.music.play();
		
		var start = new PokerGame.TextButton(this, this.world.width/2, this.world.height/4, 'Start Game', this.startGame, this);
		this.world.add(start);
		
		var room = new PokerGame.TextButton(this, this.world.width/2, this.world.height/2, 'Play With People', this.gotoRoom, this);
		this.world.add(room);
		
		var reg = new PokerGame.TextButton(this, this.world.width/2, this.world.height * 3/4, 'Anything Else', this.gotoReg, this);
		this.world.add(reg);
		
	},

	update: function () {

	},

	startGame: function () {

		//this.music.stop();
		this.state.start('Game');

	},
	
	gotoRoom: function () {

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
