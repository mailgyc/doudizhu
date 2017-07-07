PG = {
    score: 0,
    music: null,
    playerInfo: {},
    orientated: false
};


PG.getCookie = function(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

PG.PW = 90;
PG.PH = 120;

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
        this.scale.forceOrientation(true);
        this.scale.enterIncorrectOrientation.add(this.enterIncorrectOrientation, this);
        this.scale.leaveIncorrectOrientation.add(this.leaveIncorrectOrientation, this);
        this.state.start('Preloader');

        if (!this.storageAvailable('localStorage')) {
            window.localStorage = {};
            console.log('unsupported localStorage');
        }
    },

    enterIncorrectOrientation: function () {
       PG.orientated = false;
       document.getElementById('orientation').style.display = 'block';
    },

    leaveIncorrectOrientation: function () {
       PG.orientated = true;
       document.getElementById('orientation').style.display = 'none';
    },

    storageAvailable: function(type) {
        try {
            var storage = window[type],
                x = '__storage_test__';
            storage.setItem(x, x);
            storage.removeItem(x);
            return true;
        }catch(e) {
            return false;
        }
    }

};

PG.Preloader = function (game) {
	this.preloadBar = null;
};

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
        PG.RuleList = this.cache.getJSON('rule');
	    if (localStorage['username']) {
            this.state.start('MainMenu');
        } else {
	        this.state.start('Login');
        }
		// PG.music = this.add.audio('music_bg');
		// PG.music.loop = true;
		// PG.music.loopFull();
		// PG.music.play();
	}
};

PG.MainMenu = function (game) {
    this.netstat = null;
};

PG.MainMenu.prototype = {

	create: function () {
        PG.Socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));

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

		this.netstat = this.add.sprite(this.world.width - 4, 4, 'wifi_error.png');
		this.netstat.anchor.set(1, 0);
	},

    onopen: function() {
	    this.netstat.frameName = 'wifi.png';
        this.send_message([PG.Protocol.REQ_LOGIN]);
    },

    onmessage: function(packet) {
        var opcode = packet[0];
        switch (opcode) {
            case PG.Protocol.RSP_LOGIN:
                PG.playerInfo['uid'] = packet[1];
                PG.playerInfo['name'] = packet[2];
                this.send_message([PG.Protocol.REQ_JOIN_TABLE, -1]);
                break;
        }
    },

    onerror: function() {
        this.netstat.frameName = 'wifi_error.png';
    },

    startGame: function () {
	    if (this.netstat.frameName == 'wifi.png') {
            PG.gameType = 0;
            this.state.start('Game');
            //this.music.stop();
        } else {
	        alert('请检查网络连接');
        }
	},

	gotoRoom: function () {
		PG.gameType = 1;
		this.state.start('Game')
	},

	gotoSetting: function () {
		var style = { font: "22px Arial", fill: "#ffffff", align: "center" };
		var text = this.add.text(0, 0, "hei hei hei hei", style);
		var tween = this.add.tween(text).to( { x: 600, y: 450 }, 2000, "Linear", true);
		tween.onComplete.add(Phaser.Text.prototype.destroy, text);
	}
};

PG.Login = function (game) {
    this.username = null;
    this.password = null;
    this.passwordAgain = null;
    this.error = null;
};

PG.Login.prototype = {

	create: function () {
		this.stage.backgroundColor = '#182d3b';
		var bg = this.add.sprite(this.game.width/2, 0, 'bg');
		bg.anchor.set(0.5, 0);

		var style = {
            font: '24px Arial', fill: '#000', width: 300, padding: 12,
            borderWidth: 1, borderColor: '#000', borderRadius: 2,
            textAlign: 'center', placeHolder: '姓名'
            // type: PhaserInput.InputType.password
        };
        this.game.add.plugin(PhaserInput.Plugin);

        this.username = this.add.inputField((this.world.width-300)/2, this.world.height/2 - 130, style);

        style.placeHolder = '密码';
        this.password = this.add.inputField((this.world.width-300)/2, this.world.height/2 - 65, style);

        style.placeHolder = '再次输入密码';
        this.passwordAgain = this.add.inputField((this.world.width-300)/2, this.world.height/2, style);

        var style = {font: "22px Arial", fill: "#f00", align: "center"};
        this.error = this.add.text(this.world.width/2, this.world.height/2 + 20, '', style);

		var login = this.add.button(this.world.width/2, this.world.height * 3/4, 'btn', this.onLogin, this, 'register.png', 'register.png', 'register.png');
		login.anchor.set(0.5);
	},

	onLogin: function () {
        if (!this.username.value) { this.username.startFocus(); return; }
        if (!this.password.value) { this.password.startFocus(); return; }
        if (!this.passwordAgain.value) { this.passwordAgain.startFocus(); return; }
        if (this.password.value != this.passwordAgain.value) { this.error.text="两次输入的密码不一致"; return; }

        var httpRequest = new XMLHttpRequest();
        httpRequest.onreadystatechange = function(){
            if (httpRequest.readyState === XMLHttpRequest.DONE) {
                if (httpRequest.status === 200) {
                    this.state.start('MainMenu');
                    console.log(httpRequest.responseText);
                } else {
                    console.log('Error:' + httpRequest.status);
                    this.error.text = httpRequest.responseText;
                }
            }
        };
        httpRequest.open('POST', '/reg', true);
        httpRequest.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        httpRequest.setRequestHeader('X-Csrftoken', PG.getCookie("_xsrf"))

        var req = 'username=' + encodeURIComponent(this.username.value) + '&password=' + encodeURIComponent(this.password.value);
        httpRequest.send(req);
	}
};
