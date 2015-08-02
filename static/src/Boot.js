PokerGame = {

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
        this.scale.minWidth = 800;
        this.scale.minHeight = 480;
        this.scale.maxWidth = window.innerWidth * window.innerHeight/480;
        this.scale.maxHeight = window.innerHeight;
        this.scale.pageAlignHorizontally = true;
        this.scale.pageAlignVertically = true;
        this.scale.forceOrientation(true, false);
        this.scale.setResizeCallback(this.gameResized, this);
        this.scale.enterIncorrectOrientation.add(this.enterIncorrectOrientation, this);
        this.scale.leaveIncorrectOrientation.add(this.leaveIncorrectOrientation, this);
        this.scale.setScreenSize(true);

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

PokerGame.TextButton = function(game, x, y, text, callback, callbackContext)
{
    Phaser.Button.call(this, game, x, y, '', callback, callbackContext);
    
    this.backgroundColor = '#182d3b';
    this.anchor.set(0.5)
    
    this.style = {
        'font': '22px Arial',
        'fill': 'black'
    };   
    this.text = new Phaser.Text(game, 0, 0, text, this.style);
    this.addChild(this.text);
    this.setText(text);
};

PokerGame.TextButton.prototype = Object.create(Phaser.Button.prototype);
PokerGame.TextButton.prototype.constructor = PokerGame.TextButton;

PokerGame.TextButton.prototype.setText = function(text)
{
    this.text.setText(text)
    this.text.x = Math.floor((this.width - this.text.width)*0.5);
    this.text.y = Math.floor((this.height - this.text.height)*0.5);
};
