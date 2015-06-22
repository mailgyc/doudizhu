
PokerGame.Preloader = function (game) {

	this.background = null;
	this.preloadBar = null;

	this.ready = false;

};

PokerGame.PW = 90;
PokerGame.PH = 120;

PokerGame.Preloader.prototype = {

	preload: function () {

		this.preloadBar = this.add.sprite(120, 200, 'preloaderBar');
		this.load.setPreloadSprite(this.preloadBar);
		
		// this.load.audio('bg_music', 'static/assets/bgmusic.ogg');
		this.load.spritesheet('icon', 'static/assets/icon.png', 82, 84);
		this.load.spritesheet('poker', 'static/assets/poker.png', 90, 120);
		this.load.json('rule', 'static/assets/rule.json');

	},

	create: function () {

		this.state.start('MainMenu');
		PokerGame.Rule.ruleList = this.cache.getJSON('rule');

	},

	update: function () {

		// if (this.cache.isSoundDecoded('titleMusic') && this.ready == false)
		// {
			// this.ready = true;
			// this.state.start('bg_music');
		// }

	}

};
