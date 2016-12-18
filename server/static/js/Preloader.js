
PokerGame.Preloader = function (game) {

	this.background = null;
	this.preloadBar = null;
};

PokerGame.PW = 90;
PokerGame.PH = 120;

PokerGame.Preloader.prototype = {

	preload: function () {

		this.preloadBar = this.add.sprite(120, 200, 'preloaderBar');
		this.load.setPreloadSprite(this.preloadBar);
		
		this.load.audio('music_bg',   'static/audio/music_bg2.ogg');
		this.load.audio('music_deal', 'static/audio/music_deal.ogg');
		this.load.audio('music_game', 'static/audio/music_game.ogg');
		this.load.audio('music_win',  'static/audio/music_win.ogg');
		this.load.audio('music_lose', 'static/audio/music_lose.ogg');
		this.load.atlas('button', 'static/i/button.png', 'static/i/button.json');
		this.load.image('bg_1', 'static/i/bg_1.png');
		//this.load.image('bg_2', 'static/i/bg_2.png');
		this.load.spritesheet('poker',  'static/i/poker.png', 90, 120);
		this.load.json('rule', 'static/rule.json');
	},

	create: function () {
		this.state.start('MainMenu');
		//this.state.start('Game');
		PokerGame.Rule.ruleList = this.cache.getJSON('rule');

		// PokerGame.music = this.add.audio('music_bg');
		// PokerGame.music.loop = true;
		// PokerGame.music.loopFull();
		// PokerGame.music.play();
	},

};
