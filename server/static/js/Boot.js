PokerGame = {

    gameType:0, // 0 single  1 network
    score: 0,
    music: null,
    orientated: false
   
};

PokerGame.Boot = function (game) {
};

PokerGame.Boot.prototype = {

    preload: function () {

        this.load.image('preloaderBar', 'static/assets/preload.png');

    },

    create: function () {

        this.input.maxPointers = 1;
        this.stage.disableVisibilityChange = true;
        this.scale.scaleMode = Phaser.ScaleManager.SHOW_ALL;
        this.scale.aspectRatio = true;
        this.scale.maxWidth = this.game.width;
        this.scale.maxHeight = this.game.height;
        this.scale.pageAlignHorizontally = true;
        this.scale.pageAlignVertically = true;
        this.scale.forceOrientation(true, false);
        this.scale.setResizeCallback(this.gameResized, this);
        this.scale.enterIncorrectOrientation.add(this.enterIncorrectOrientation, this);
        this.scale.leaveIncorrectOrientation.add(this.leaveIncorrectOrientation, this);

        this.state.start('Preloader');
        
    },

    gameResized: function (width, height) {
    },

    enterIncorrectOrientation: function () {

       PokerGame.orientated = false;
       document.getElementById('orientation').style.display = 'block';

    },

    leaveIncorrectOrientation: function () {

       PokerGame.orientated = true;
       document.getElementById('orientation').style.display = 'none';

    }

}
