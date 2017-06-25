PG = {
    score: 0,
    music: null,
    orientated: false
};

PG.Boot = function (game) {
};

PG.Boot.prototype = {

    preload: function () {
        this.load.image('preloaderBar', 'static/i/preload.png');
    },

    create: function () {
        this.input.maxPointers = 1;
        this.stage.disableVisibilityChange = true;
        this.scale.scaleMode = Phaser.ScaleManager.SHOW_ALL;
        this.scale.minWidth = 960;
        this.scale.minHeight = 540;
        this.scale.maxWidth = window.innerWidth;
        this.scale.maxHeight = window.innerHeight;
        this.scale.pageAlignHorizontally = true;
        this.scale.pageAlignVertically = true;
        this.scale.forceOrientation(true, false);
        this.scale.setResizeCallback(this.gameResized, this);
        this.scale.enterIncorrectOrientation.add(this.enterIncorrectOrientation, this);
        this.scale.leaveIncorrectOrientation.add(this.leaveIncorrectOrientation, this);
        //this.scale.setScreenSize(true);
        this.state.start('Preloader');
    },

    gameResized: function (width, height) {
    },

    enterIncorrectOrientation: function () {
       PG.orientated = false;
       document.getElementById('orientation').style.display = 'block';
    },

    leaveIncorrectOrientation: function () {
       PG.orientated = true;
       document.getElementById('orientation').style.display = 'none';
    }
};

PG.Preloader = function (game) {
	this.preloadBar = null;
};

PG.PW = 90;
PG.PH = 120;

PG.Preloader.prototype = {
	preload: function () {
		this.preloadBar = this.add.sprite(120, 200, 'preloaderBar');
		this.load.setPreloadSprite(this.preloadBar);

		this.load.audio('music_bg',   'static/audio/music_bg2.ogg');
		this.load.audio('music_deal', 'static/audio/music_deal.ogg');
		this.load.audio('music_game', 'static/audio/music_game.ogg');
		this.load.audio('music_win',  'static/audio/music_win.ogg');
		this.load.audio('music_lose', 'static/audio/music_lose.ogg');
		this.load.atlas('btn', 'static/i/btn.png', 'static/i/btn.json');
		this.load.image('bg', 'static/i/bg.png');
		this.load.spritesheet('poker',  'static/i/poker.png', 90, 120);
		this.load.json('rule', 'static/rule.json');
	},

	create: function () {
		this.state.start('MainMenu');
		PG.Rule.ruleList = this.cache.getJSON('rule');
		// PG.music = this.add.audio('music_bg');
		// PG.music.loop = true;
		// PG.music.loopFull();
		// PG.music.play();
	}
};

PG.MainMenu = function (game) {
};

PG.MainMenu.prototype = {

	create: function () {

		this.stage.backgroundColor = '#182d3b';

		var bg = this.add.sprite(this.game.width/2, 0, 'bg');
		bg.anchor.set(0.5, 0);

		var quick = this.add.button(this.world.width/2, this.world.height/4, 'btn', this.startGame, this, 'quick.png', 'quick.png', 'quick.png');
		quick.anchor.set(0.5);
		this.world.add(quick);

		var start = this.add.button(this.world.width/2, this.world.height/2, 'btn', this.gotoRoom, this, 'start.png', 'start.png', 'start.png');
		start.anchor.set(0.5);
		this.world.add(start);

		var setting = this.add.button(this.world.width/2, this.world.height * 3/4, 'btn', this.gotoSetting, this, 'setting.png', 'setting.png', 'setting.png');
		setting.anchor.set(0.5);
		this.world.add(setting);
	},

	update: function () {

	},

	startGame: function () {
		PG.gameType = 0;
		this.state.start('Game');
		//this.music.stop();
	},

	gotoRoom: function () {
		PG.gameType = 1;
		this.state.start('Game')
	},

	gotoSetting: function () {
		var style = { font: "22px Arial", fill: "#ffffff", align: "center" };
		var text = this.add.text(0, 0, "hei hei hei hei", style);
		var tween = this.add.tween(text).to( { x: 600, y: 450 }, 2000, "Linear", true);
		//tween.onComplete.add(text.destroy, text);
		tween.onComplete.add(Phaser.Text.prototype.destroy, text);
	}

};
